"""Sentence segmentation tuned to central bank prose.

Central bank documents break generic sentence splitters in a few specific
ways: decimal numbers ("2.5 per cent"), abbreviations (U.S., a.m., Messrs.),
enumerated clauses in FOMC minutes ("(1) ...; (2) ..."), and very long
sentences glued together with semicolons. The rules here handle those cases
explicitly rather than relying on a statistical model, so segmentation is
deterministic and auditable.
"""

import re
from typing import List

# Abbreviations that end with a period but do not end a sentence.
_ABBREVIATIONS = {
    "u.s", "u.k", "mr", "mrs", "ms", "dr", "gov", "govs", "st", "jr", "sr",
    "vs", "no", "vol", "pp", "p.m", "a.m", "i.e", "e.g", "etc", "cf",
    "messrs", "prof", "rev", "sec", "chg", "corp", "inc", "ltd", "co",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sept", "sep", "oct",
    "nov", "dec", "q1", "q2", "q3", "q4",
}

# A sentence boundary: terminal punctuation, whitespace, then something that
# plausibly starts a sentence (capital letter, digit, or an open quote/paren).
_BOUNDARY_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"“(])')

# Semicolon boundaries are split only when both sides are substantial
# clauses; short-side semicolons (lists of numbers, statute citations) stay.
_SEMICOLON_MIN_CLAUSE_CHARS = 60

# Enumerated clause markers used in FOMC minutes.
_ENUM_RE = re.compile(r";\s*(?:and\s+)?(?=\(\d+\)|\([a-z]\)\s)")

_WS_RE = re.compile(r"\s+")

_MIN_SENTENCE_CHARS = 20


def _ends_with_abbreviation(chunk: str) -> bool:
    tail = chunk.rstrip()
    if not tail.endswith("."):
        return False
    last_token = tail[:-1].rsplit(None, 1)[-1] if tail[:-1].strip() else ""
    last_token = last_token.lstrip("(\"'“").lower()
    if last_token in _ABBREVIATIONS:
        return True
    # Single capital letter initial, e.g. "John Q. Public".
    if len(last_token) == 1 and last_token.isalpha():
        return True
    # Dotted acronyms like "U.S." keep their internal periods.
    if re.fullmatch(r"(?:[a-z]\.)+[a-z]?", last_token):
        return True
    return False


def _split_terminal(text: str) -> List[str]:
    """Split on terminal punctuation, then re-join false splits."""
    pieces = _BOUNDARY_RE.split(text)
    merged: List[str] = []
    for piece in pieces:
        if merged and _ends_with_abbreviation(merged[-1]):
            merged[-1] = merged[-1] + " " + piece
        else:
            merged.append(piece)
    return merged


def _split_semicolons(sentence: str) -> List[str]:
    """Split a long sentence at semicolons when both sides stand alone.

    FOMC minutes routinely chain three or more full clauses with semicolons;
    each clause carries its own stance and should be scored separately.
    """
    if ";" not in sentence:
        return [sentence]

    # Enumerated clauses always split.
    parts = _ENUM_RE.split(sentence)
    out: List[str] = []
    for part in parts:
        clauses = part.split(";")
        buf = clauses[0]
        for clause in clauses[1:]:
            if (
                len(buf.strip()) >= _SEMICOLON_MIN_CLAUSE_CHARS
                and len(clause.strip()) >= _SEMICOLON_MIN_CLAUSE_CHARS
            ):
                out.append(buf)
                buf = clause
            else:
                buf = buf + ";" + clause
        out.append(buf)
    return out


def _clean(sentence: str) -> str:
    s = _WS_RE.sub(" ", sentence).strip()
    s = s.strip("; ")
    # Leading enumeration markers like "(2)" carry no content.
    s = re.sub(r"^\(\d+\)\s*", "", s)
    s = re.sub(r"^\([a-z]\)\s*", "", s)
    return s.strip()


def segment_sentences(text: str) -> List[str]:
    """Segment a central bank document into scoring units.

    Returns cleaned sentences in document order. Very short fragments
    (page numbers, table headers, vote tallies shorter than a clause)
    are dropped.
    """
    if not text or not text.strip():
        return []

    normalized = _WS_RE.sub(" ", text).strip()

    sentences: List[str] = []
    for chunk in _split_terminal(normalized):
        for clause in _split_semicolons(chunk):
            cleaned = _clean(clause)
            if len(cleaned) >= _MIN_SENTENCE_CHARS:
                sentences.append(cleaned)
    return sentences
