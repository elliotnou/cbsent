"""Dictionary-based hawkish/dovish classification.

Implements the noun-plus-direction co-occurrence method of Apel & Blix
Grimaldi (2012), "The Information Content of Central Bank Minutes",
Sveriges Riksbank Working Paper No. 261: a sentence is hawkish when a
pressure noun co-occurs with an upward modifier (or a policy-tightening
expression appears), dovish in the mirrored case, and the sentence label
is the sign of the hawkish-minus-dovish expression count.

Word lists follow the paper's taxonomy, extended with the balance-sheet
and guidance vocabulary of the post-2008 era so the comparison against
modern text is fair rather than strawmanned. This module is both a Phase 4
baseline and a bootstrap labeller; it is intentionally negation-blind, as
the published method is.
"""

import re
from typing import Literal

NOUNS = [
    "inflation", "price", "prices", "cost", "costs", "wage", "wages",
    "economic activity", "activity", "growth", "demand", "employment",
    "labor market", "labour market", "output", "spending", "consumption",
    "pressure", "pressures", "expectations",
]

UP_MODIFIERS = [
    "increase", "increases", "increased", "increasing", "rise", "rises",
    "risen", "rising", "rose", "higher", "high", "elevated", "strong",
    "stronger", "strengthened", "strengthening", "robust", "solid",
    "picked up", "pick up", "accelerated", "accelerating", "upward",
    "above target", "overheating", "tight", "tighter",
]

DOWN_MODIFIERS = [
    "decrease", "decreases", "decreased", "decreasing", "decline",
    "declines", "declined", "declining", "fall", "falls", "fallen",
    "falling", "fell", "lower", "low", "subdued", "weak", "weaker",
    "weakened", "weakening", "soft", "softened", "softening", "muted",
    "slowed", "slowing", "slower", "eased", "easing", "moderated",
    "moderating", "downward", "below target", "slack",
]

HAWKISH_POLICY = [
    "raise the target range", "raised the target range",
    "raise the policy rate", "raised the policy rate",
    "increase the policy interest rate", "increased the policy interest rate",
    "rate increase", "rate increases", "rate hike", "policy firming",
    "tighten monetary policy", "tightening of monetary policy",
    "quantitative tightening", "balance sheet runoff", "reduce its holdings",
    "reducing its holdings", "restrictive stance", "restrictive policy",
    "withdraw accommodation", "withdrawal of accommodation",
    "removal of policy accommodation",
]

DOVISH_POLICY = [
    "lower the target range", "lowered the target range",
    "lower the policy rate", "lowered the policy rate",
    "reduce the policy interest rate", "reduced the policy interest rate",
    "cut the policy rate", "rate cut", "rate cuts", "rate reduction",
    "ease monetary policy", "easing of monetary policy", "policy easing",
    "quantitative easing", "asset purchases", "accommodative stance",
    "accommodative policy", "maintain accommodation", "provide stimulus",
    "monetary stimulus", "forward guidance on lower",
]

Label = Literal["hawkish", "dovish", "neutral"]

_WORD_RES = {}


def _contains(text_lower: str, term: str) -> bool:
    """Whole-word match; multi-word terms match as phrases."""
    if term not in _WORD_RES:
        _WORD_RES[term] = re.compile(r"\b" + re.escape(term) + r"\b")
    return _WORD_RES[term].search(text_lower) is not None


def _count_matches(text_lower: str, terms) -> int:
    return sum(1 for t in terms if _contains(text_lower, t))


def score(text: str) -> int:
    """Hawkish-minus-dovish expression count for one sentence.

    A noun-modifier pair counts once per distinct modifier present, at
    sentence granularity, matching the unit the published method scores.
    """
    text_lower = text.lower()
    has_noun = any(_contains(text_lower, n) for n in NOUNS)

    hawk = _count_matches(text_lower, UP_MODIFIERS) if has_noun else 0
    hawk += _count_matches(text_lower, HAWKISH_POLICY)
    dove = _count_matches(text_lower, DOWN_MODIFIERS) if has_noun else 0
    dove += _count_matches(text_lower, DOVISH_POLICY)
    return hawk - dove


def classify(text: str) -> Label:
    s = score(text)
    if s > 0:
        return "hawkish"
    if s < 0:
        return "dovish"
    return "neutral"
