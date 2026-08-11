"""Public scoring API.

    from cbsent import score
    score("Inflation remains elevated and the labour market is tight.")

Weights are loaded once per process from a local export directory or the
Hugging Face Hub, whichever is configured.
"""

import os
from functools import lru_cache
from typing import List, Optional

from cbsent.model import TOPIC_LABELS, Scorer
from cbsent.segment import segment_sentences

DEFAULT_LOCAL_DIR = "export/cbsent"
HUB_REPO_ENV = "CBSENT_HUB_REPO"
LOCAL_DIR_ENV = "CBSENT_MODEL_DIR"

# Topic weights for document aggregation. Sentences about the policy
# decision and inflation move the pair; growth and labour detail matter
# less, and financial stability language is largely descriptive.
TOPIC_WEIGHTS = {
    "guidance": 1.0,
    "inflation": 1.0,
    "employment": 0.7,
    "growth": 0.7,
    "financial_stability": 0.3,
}


def _resolve_model_dir() -> str:
    local = os.getenv(LOCAL_DIR_ENV, DEFAULT_LOCAL_DIR)
    if os.path.exists(os.path.join(local, "model.pt")):
        return local
    repo = os.getenv(HUB_REPO_ENV)
    if repo:
        from huggingface_hub import snapshot_download
        return snapshot_download(repo_id=repo)
    raise FileNotFoundError(
        f"no model found at {local}; train one with scripts/train.py or set "
        f"{HUB_REPO_ENV} to a Hugging Face repo id"
    )


@lru_cache(maxsize=2)
def _scorer(model_dir: Optional[str] = None) -> Scorer:
    return Scorer(model_dir or _resolve_model_dir())


def score_sentences(sentences: List[str], model_dir: Optional[str] = None) -> List[dict]:
    """Score pre-segmented sentences."""
    return _scorer(model_dir).score_sentences(sentences)


def score(text: str, model_dir: Optional[str] = None) -> dict:
    """Score a document or passage.

    Returns the topic-weighted document score in [-1, 1], the stance
    implied by its sign, and the per-sentence detail.
    """
    sentences = segment_sentences(text)
    results = score_sentences(sentences, model_dir)

    numerator = denominator = 0.0
    for r in results:
        w = TOPIC_WEIGHTS.get(r["topic"], 0.5)
        numerator += r["score"] * w
        denominator += w
    doc_score = numerator / denominator if denominator else 0.0

    if doc_score > 0.05:
        stance = "hawkish"
    elif doc_score < -0.05:
        stance = "dovish"
    else:
        stance = "neutral"

    return {
        "score": round(doc_score, 4),
        "stance": stance,
        "n_sentences": len(results),
        "sentences": results,
    }
