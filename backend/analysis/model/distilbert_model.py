import torch
import torch.nn as nn
from transformers import DistilBertModel

TOPIC_LABELS = ["Inflation", "Growth", "Employment", "Guidance", "Boilerplate"]

TOPIC_TO_WEIGHT = {
    "Inflation": 1.0,
    "Guidance": 1.0,
    "Employment": 0.7,
    "Growth": 0.7,
    "Boilerplate": 0.0,
}

# Maps GPT's varied topic names → canonical 5-class labels
TOPIC_ALIAS = {
    "Inflation": "Inflation",
    "Growth": "Growth",
    "Employment": "Employment",
    "Guidance": "Guidance",
    "Interest Rate Guidance": "Guidance",
    "Boilerplate": "Boilerplate",
    "Global Risks / External Factors": "Growth",
    "Global Risks": "Growth",
    "External Factors": "Growth",
    "Risk": "Growth",
    "Liquidity Risks": "Growth",
    "Liquidity": "Growth",
    "Dovish": "Guidance",
}


def normalize_topic(raw_topic: str) -> str | None:
    """Map a raw GPT topic label to one of the 5 canonical labels."""
    cleaned = raw_topic.strip().title()
    # Try exact match first
    if cleaned in TOPIC_ALIAS:
        return TOPIC_ALIAS[cleaned]
    # Try case-insensitive match
    for key, val in TOPIC_ALIAS.items():
        if key.lower() == cleaned.lower():
            return val
    return None


class MultiTaskDistilBERT(nn.Module):
    """
    Fine-tuned DistilBERT with two task heads for central bank sentiment analysis.

    Heads:
      - Regression: stance_score in [-1, 1] (hawkish/dovish) via tanh
      - Classification: topic (Inflation, Growth, Employment, Guidance, Boilerplate)

    Both heads share the [CLS] token representation from the DistilBERT backbone.
    """

    def __init__(self, num_topics=len(TOPIC_LABELS), dropout=0.3):
        super().__init__()
        self.distilbert = DistilBertModel.from_pretrained("distilbert-base-uncased")
        hidden_size = self.distilbert.config.hidden_size  # 768

        self.score_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1),
            nn.Tanh(),
        )

        self.topic_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_topics),
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.distilbert(input_ids=input_ids, attention_mask=attention_mask)
        cls_output = outputs.last_hidden_state[:, 0, :]  # [CLS] token

        score = self.score_head(cls_output).squeeze(-1)  # (batch,)
        topic_logits = self.topic_head(cls_output)  # (batch, num_topics)

        return score, topic_logits
