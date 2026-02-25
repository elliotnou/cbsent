"""
Sentiment analysis engine using a fine-tuned DistilBERT model.

Replaces the previous GPT-4o-mini implementation while keeping the same
public interface (ToneAnalyzer class, analyze_paragraph() signature and
return types) so that batch_processor.py works without changes.
"""

import os
import re
import torch
from typing import List
from pydantic import BaseModel, Field
from transformers import DistilBertTokenizer

from model.distilbert_model import (
    MultiTaskDistilBERT,
    TOPIC_LABELS,
    TOPIC_TO_WEIGHT,
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model", "export")
MAX_SEQ_LEN = 128

# ---------------------------------------------------------------------------
# Pydantic schemas (unchanged from GPT version)
# ---------------------------------------------------------------------------

class SentenceAnalysis(BaseModel):
    text: str = Field(description="The original sentence from paragraph")
    topic: str = Field(description="Primary topic: Inflation, Growth, Employment, Guidance, or Boilerplate")
    score: float = Field(description="Hawkish/Dovish score (-1.0 to 1.0)")
    weight: float = Field(description="Importance weight from 0.0 to 1.0 based on market impact")
    reasoning: str = Field(description="Brief logic for the classification")


class ParagraphAnalysis(BaseModel):
    sentences: List[SentenceAnalysis]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> List[str]:
    """Split a paragraph into sentences using regex."""
    sentences = _SENTENCE_SPLIT_RE.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _stance_label(score: float) -> str:
    """Return a human-readable stance description."""
    abs_score = abs(score)
    if abs_score < 0.2:
        intensity = "neutral"
    elif abs_score < 0.5:
        intensity = "moderate"
    else:
        intensity = "strong"

    if score > 0.05:
        direction = "hawkish"
    elif score < -0.05:
        direction = "dovish"
    else:
        return "neutral stance"

    return f"{intensity} {direction}"


# ---------------------------------------------------------------------------
# ToneAnalyzer (drop-in replacement for the GPT version)
# ---------------------------------------------------------------------------

class ToneAnalyzer:
    """Runs inference with the fine-tuned DistilBERT model."""

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Load tokenizer
        tokenizer_path = os.path.join(MODEL_DIR, "tokenizer")
        self.tokenizer = DistilBertTokenizer.from_pretrained(tokenizer_path)

        # Load model
        self.model = MultiTaskDistilBERT()
        state_dict = torch.load(
            os.path.join(MODEL_DIR, "model.pt"),
            map_location=self.device,
            weights_only=False,
        )
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

        print("DistilBERT sentiment model loaded successfully")

    def _predict_sentence(self, text: str) -> SentenceAnalysis:
        """Run a single sentence through the model."""
        encoding = self.tokenizer(
            text,
            max_length=MAX_SEQ_LEN,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            score, topic_logits = self.model(input_ids, attention_mask)

        score_val = round(float(score.item()), 3)
        topic_idx = int(topic_logits.argmax(dim=1).item())
        topic_name = TOPIC_LABELS[topic_idx]
        weight = TOPIC_TO_WEIGHT[topic_name]

        reasoning = (
            f"DistilBERT classified this as {topic_name} with a "
            f"{_stance_label(score_val)} (score: {score_val:.3f})"
        )

        return SentenceAnalysis(
            text=text,
            topic=topic_name,
            score=score_val,
            weight=weight,
            reasoning=reasoning,
        )

    def analyze_paragraph(self, text: str) -> ParagraphAnalysis:
        """Analyse a paragraph sentence-by-sentence (same API as GPT version)."""
        sentences = _split_sentences(text)
        if not sentences:
            return ParagraphAnalysis(sentences=[])

        results = [self._predict_sentence(s) for s in sentences]
        return ParagraphAnalysis(sentences=results)