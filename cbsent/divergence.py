"""Fed minus BoC hawkishness divergence, computed point-in-time.

The index at any instant uses only documents published strictly before
that instant. Each bank's level is the topic-weighted mean sentence score
of its most recent documents, with older documents down-weighted by an
exponential decay in days, so a stale statement does not carry the same
weight as this morning's.
"""

import datetime
import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from cbsent.labels import DEFAULT_TOPIC_WEIGHT, TOPIC_WEIGHTS

HALF_LIFE_DAYS = 45.0


@dataclass
class ScoredSentence:
    published_at: datetime.datetime
    bank: str
    score: float
    topic: str


def bank_level(sentences: List[ScoredSentence], asof: datetime.datetime,
               bank: str, half_life_days: float = HALF_LIFE_DAYS) -> Optional[float]:
    """Hawkishness level for one bank using only text published before asof."""
    numerator = denominator = 0.0
    for s in sentences:
        if s.bank != bank or s.published_at >= asof:
            continue
        age_days = (asof - s.published_at).total_seconds() / 86400.0
        decay = math.exp(-math.log(2) * age_days / half_life_days)
        weight = TOPIC_WEIGHTS.get(s.topic, DEFAULT_TOPIC_WEIGHT) * decay
        numerator += s.score * weight
        denominator += weight
    if denominator == 0.0:
        return None
    return numerator / denominator


def divergence(sentences: List[ScoredSentence], asof: datetime.datetime,
               half_life_days: float = HALF_LIFE_DAYS) -> Optional[float]:
    """Fed level minus BoC level as of an instant, or None if either is empty."""
    fed = bank_level(sentences, asof, "FED", half_life_days)
    boc = bank_level(sentences, asof, "BOC", half_life_days)
    if fed is None or boc is None:
        return None
    return fed - boc


def series(sentences: List[ScoredSentence], start: datetime.date,
           end: datetime.date, half_life_days: float = HALF_LIFE_DAYS) -> Dict[datetime.date, float]:
    """Daily divergence series, each day evaluated at that day's open."""
    out = {}
    day = start
    while day <= end:
        # Evaluate before the North American session so the value on a
        # decision day never contains that day's release.
        asof = datetime.datetime.combine(
            day, datetime.time(8, 0), tzinfo=datetime.timezone.utc
        )
        value = divergence(sentences, asof, half_life_days)
        if value is not None:
            out[day] = value
        day += datetime.timedelta(days=1)
    return out
