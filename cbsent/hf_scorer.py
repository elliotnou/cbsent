"""Scoring wrapper for models saved in Hugging Face format.

The benchmark track (scripts/train_benchmark.py) exports a standard
sequence-classification model rather than the two-headed checkpoint in
cbsent/model.py. This wrapper gives it the same interface, so the public
score() API works with either.

Inference runs on CPU: MPS is not deterministic for this model (measured
in RESULTS.md) and a scorer whose answers change between runs is not
worth the speed.
"""

import os
from typing import List, Optional

STANCE_ORDER = ("hawkish", "dovish", "neutral")


class HFScorer:
    def __init__(self, model_dir: str, device: Optional[str] = None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.model_dir = model_dir
        self.device = torch.device(device or "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.to(self.device)
        self.model.eval()

        self.id2label = {int(k): v for k, v in self.model.config.id2label.items()}
        self.label2id = {v: k for k, v in self.id2label.items()}
        # Topic prediction belongs to the two-headed model; this one is
        # stance-only, so every sentence carries the same aggregation weight.
        self.has_topic = False

    def fingerprint(self) -> str:
        import hashlib

        h = hashlib.sha256()
        for name in ("model.safetensors", "pytorch_model.bin"):
            path = os.path.join(self.model_dir, name)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    while chunk := f.read(1 << 20):
                        h.update(chunk)
                break
        return f"{h.hexdigest()[:16]}:{self.device}"

    def score_sentences(self, sentences: List[str], batch_size: int = 32) -> List[dict]:
        if not sentences:
            return []
        torch = self.torch
        hawk, dove = self.label2id["hawkish"], self.label2id["dovish"]
        results = []
        with torch.no_grad():
            for start in range(0, len(sentences), batch_size):
                batch = sentences[start:start + batch_size]
                enc = self.tokenizer(batch, max_length=128, padding=True,
                                     truncation=True, return_tensors="pt").to(self.device)
                probs = self.model(**enc).logits.softmax(dim=-1).cpu()
                for i, sentence in enumerate(batch):
                    p = probs[i]
                    results.append({
                        "text": sentence,
                        "stance": self.id2label[int(p.argmax())],
                        # Signed scalar in [-1, 1]: P(hawkish) - P(dovish).
                        "score": round(float(p[hawk]) - float(p[dove]), 4),
                        "confidence": round(float(p.max()), 4),
                        "topic": None,
                    })
        return results


def is_hf_export(model_dir: str) -> bool:
    """True when a directory holds a Hugging Face model rather than model.pt."""
    if not os.path.isdir(model_dir):
        return False
    has_config = os.path.exists(os.path.join(model_dir, "config.json"))
    has_weights = any(
        os.path.exists(os.path.join(model_dir, n))
        for n in ("model.safetensors", "pytorch_model.bin")
    )
    return has_config and has_weights
