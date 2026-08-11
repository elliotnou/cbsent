"""Multi-task DistilBERT: stance (hawkish/dovish/neutral) + topic.

Both heads share the [CLS] representation. Stance is 3-class
classification — the evaluation metric across the engine and both
baselines is macro-F1 on the same held-out year, so all three systems
speak the same label space.
"""

import json
import os
from typing import List, Optional

import torch
import torch.nn as nn
from transformers import DistilBertModel, DistilBertTokenizerFast

from cbsent.labels import STANCES, TOPICS
from cbsent.negation import mark_cues, special_tokens

STANCE_LABELS: List[str] = list(STANCES)
TOPIC_LABELS: List[str] = list(TOPICS)

BACKBONE = "distilbert-base-uncased"
MAX_SEQ_LEN = 96


def pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class CBSentModel(nn.Module):
    def __init__(self, dropout: float = 0.2):
        super().__init__()
        self.distilbert = DistilBertModel.from_pretrained(BACKBONE)
        hidden = self.distilbert.config.hidden_size

        self.stance_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden, len(STANCE_LABELS)),
        )
        self.topic_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden, len(TOPIC_LABELS)),
        )

    def forward(self, input_ids, attention_mask):
        out = self.distilbert(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        return self.stance_head(cls), self.topic_head(cls)


def build_tokenizer(use_negation_markers: bool) -> DistilBertTokenizerFast:
    tokenizer = DistilBertTokenizerFast.from_pretrained(BACKBONE)
    if use_negation_markers:
        tokenizer.add_special_tokens({"additional_special_tokens": special_tokens()})
    return tokenizer


class Scorer:
    """Inference wrapper: text in, stance/topic out."""

    def __init__(self, model_dir: str, device: Optional[str] = None):
        with open(os.path.join(model_dir, "config.json"), encoding="utf-8") as f:
            self.config = json.load(f)
        self.use_negation_markers = self.config["use_negation_markers"]

        self.device = torch.device(device) if device else pick_device()
        self.tokenizer = DistilBertTokenizerFast.from_pretrained(
            os.path.join(model_dir, "tokenizer")
        )
        self.model = CBSentModel()
        if self.use_negation_markers:
            self.model.distilbert.resize_token_embeddings(len(self.tokenizer))
        state = torch.load(
            os.path.join(model_dir, "model.pt"),
            map_location="cpu", weights_only=True,
        )
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def score_sentences(self, sentences: List[str]) -> List[dict]:
        if not sentences:
            return []
        texts = [mark_cues(s) for s in sentences] if self.use_negation_markers else sentences
        enc = self.tokenizer(
            texts, max_length=MAX_SEQ_LEN, padding=True, truncation=True,
            return_tensors="pt",
        ).to(self.device)
        stance_logits, topic_logits = self.model(enc["input_ids"], enc["attention_mask"])
        stance_probs = stance_logits.softmax(dim=-1).cpu()
        topic_idx = topic_logits.argmax(dim=-1).cpu()

        results = []
        for i, sentence in enumerate(sentences):
            probs = stance_probs[i]
            stance = STANCE_LABELS[int(probs.argmax())]
            # Signed scalar in [-1, 1]: P(hawkish) - P(dovish).
            hawk = float(probs[STANCE_LABELS.index("hawkish")])
            dove = float(probs[STANCE_LABELS.index("dovish")])
            results.append({
                "text": sentence,
                "stance": stance,
                "score": round(hawk - dove, 4),
                "topic": TOPIC_LABELS[int(topic_idx[i])],
            })
        return results
