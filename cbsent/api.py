"""Public scoring API.

    from cbsent import score
    score("Inflation remains elevated and the labour market is tight.")

Weights are loaded once per process from a local export directory or the
Hugging Face Hub, whichever is configured.
"""

import os
from functools import lru_cache
from typing import List, Optional

from cbsent.hf_scorer import HFScorer, is_hf_export
from cbsent.labels import DEFAULT_TOPIC_WEIGHT, TOPIC_WEIGHTS
from cbsent.segment import segment_sentences

HUB_REPO_ENV = "CBSENT_HUB_REPO"
LOCAL_DIR_ENV = "CBSENT_MODEL_DIR"

# Searched in order. The benchmark fine-tune is the better scorer and is
# preferred; the two-headed model is the fallback because it also predicts
# topic, which document aggregation uses when available.
DEFAULT_MODEL_DIRS = (
    "export/cbsent-bench",
    "export/bench-sweep/boc1200-20250811",
    "export/cbsent",
)


def _resolve_model_dir() -> str:
    override = os.getenv(LOCAL_DIR_ENV)
    candidates = (override,) if override else DEFAULT_MODEL_DIRS
    for local in candidates:
        if is_hf_export(local) or os.path.exists(os.path.join(local, "model.pt")):
            return local
    repo = os.getenv(HUB_REPO_ENV)
    if repo:
        from huggingface_hub import snapshot_download
        return snapshot_download(repo_id=repo)
    raise FileNotFoundError(
        "no model found in " + ", ".join(c for c in candidates if c) +
        f"; train one (make train-benchmark) or set {HUB_REPO_ENV} to a "
        "Hugging Face repo id"
    )


@lru_cache(maxsize=2)
def _scorer(model_dir: Optional[str] = None):
    resolved = model_dir or _resolve_model_dir()
    if is_hf_export(resolved):
        return HFScorer(resolved)
    from cbsent.model import Scorer
    return Scorer(resolved)


def score_sentences(sentences: List[str], model_dir: Optional[str] = None) -> List[dict]:
    """Score pre-segmented sentences."""
    return _scorer(model_dir).score_sentences(sentences)


NEUTRAL_BAND = 0.05


def aggregate(results: List[dict]) -> dict:
    """Combine scored sentences into a topic-weighted document score."""
    numerator = denominator = 0.0
    for r in results:
        w = TOPIC_WEIGHTS.get(r["topic"], DEFAULT_TOPIC_WEIGHT)
        numerator += r["score"] * w
        denominator += w
    doc_score = numerator / denominator if denominator else 0.0

    if doc_score > NEUTRAL_BAND:
        stance = "hawkish"
    elif doc_score < -NEUTRAL_BAND:
        stance = "dovish"
    else:
        stance = "neutral"

    return {
        "score": round(doc_score, 4),
        "stance": stance,
        "n_sentences": len(results),
        "sentences": results,
    }


def score(text: str, model_dir: Optional[str] = None) -> dict:
    """Score a document or passage.

    Returns the topic-weighted document score in [-1, 1], the stance
    implied by its sign, and the per-sentence detail.
    """
    sentences = segment_sentences(text)
    return aggregate(score_sentences(sentences, model_dir))
