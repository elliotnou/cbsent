"""Label vocabulary and aggregation weights.

Kept free of heavy imports so the ingest, dictionary and event-study code
paths do not pull in PyTorch.
"""

STANCES = ("hawkish", "dovish", "neutral")
TOPICS = ("inflation", "employment", "growth", "financial_stability", "guidance")

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

DEFAULT_TOPIC_WEIGHT = 0.5
