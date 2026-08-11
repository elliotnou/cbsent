import pytest

torch = pytest.importorskip("torch")

from cbsent.api import aggregate


def s(score, topic):
    return {"text": "x", "stance": "neutral", "score": score, "topic": topic}


def test_empty_document_is_neutral_zero():
    out = aggregate([])
    assert out["score"] == 0.0
    assert out["stance"] == "neutral"
    assert out["n_sentences"] == 0


def test_single_sentence_passes_through():
    assert aggregate([s(0.8, "guidance")])["score"] == 0.8


def test_full_weight_topics_dominate_partial_ones():
    # guidance weight 1.0 hawkish against growth weight 0.7 dovish
    out = aggregate([s(1.0, "guidance"), s(-1.0, "growth")])
    assert out["score"] > 0
    assert out["stance"] == "hawkish"


def test_financial_stability_is_discounted():
    out = aggregate([s(-1.0, "financial_stability"), s(0.5, "inflation")])
    assert out["stance"] == "hawkish"


def test_neutral_band_suppresses_tiny_scores():
    assert aggregate([s(0.04, "guidance")])["stance"] == "neutral"
    assert aggregate([s(-0.04, "guidance")])["stance"] == "neutral"


def test_unknown_topic_uses_default_weight():
    out = aggregate([s(1.0, "not_a_topic")])
    assert out["score"] == 1.0
