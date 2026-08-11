"""Rule-based negation and hedge cue marking.

The model's negation handling is an input transform: cue words are
prefixed with inline markers ([NEG], [HEDGE]) that are registered as
special tokens, so the encoder sees negation scope explicitly instead of
having to infer it from sparse training data. Phase 3 ablates this
transform (train with vs. without) to measure its effect.

Cue inventories draw on the negation and uncertainty word lists of
Loughran & McDonald (2011) trimmed to what actually occurs in central
bank prose.
"""

import re
from typing import List

NEG_TOKEN = "[NEG]"
HEDGE_TOKEN = "[HEDGE]"

NEGATION_CUES = [
    "not", "no", "never", "without", "neither", "nor", "cannot",
    "n't", "no longer", "not yet", "does not", "do not", "did not",
    "will not", "would not", "should not", "is not", "are not", "was not",
    "were not", "has not", "have not", "had not", "unlikely", "less likely",
]

HEDGE_CUES = [
    "may", "might", "could", "possibly", "perhaps", "somewhat", "likely",
    "appears", "appear", "seems", "seem", "suggests", "suggest",
    "expected to", "anticipates", "anticipate", "if", "should the",
    "depending on", "uncertain", "uncertainty", "risks", "risk",
    "in the event", "were to", "would depend", "data-dependent",
]

# Longest-first so multi-word cues win over their prefixes.
_ALL_CUES = sorted(
    [(c, NEG_TOKEN) for c in NEGATION_CUES] + [(c, HEDGE_TOKEN) for c in HEDGE_CUES],
    key=lambda x: -len(x[0]),
)
_CUE_RE = re.compile(
    r"\b(" + "|".join(re.escape(c) for c, _ in _ALL_CUES) + r")\b",
    re.IGNORECASE,
)
_CUE_TO_TOKEN = {c.lower(): t for c, t in _ALL_CUES}


def mark_cues(text: str) -> str:
    """Prefix each negation/hedge cue with its marker token."""

    def _sub(m: re.Match) -> str:
        token = _CUE_TO_TOKEN[m.group(1).lower()]
        return f"{token} {m.group(1)}"

    return _CUE_RE.sub(_sub, text)


def special_tokens() -> List[str]:
    return [NEG_TOKEN, HEDGE_TOKEN]
