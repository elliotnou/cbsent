"""cbsent: hawkish-dovish sentiment engine for central bank communications."""

from cbsent.segment import segment_sentences

__all__ = ["score", "score_sentences", "segment_sentences"]
__version__ = "0.1.0"


def __getattr__(name):
    # Torch is only needed for scoring, so the import is deferred; this
    # keeps `from cbsent import segment_sentences` cheap.
    if name in ("score", "score_sentences"):
        from cbsent import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
