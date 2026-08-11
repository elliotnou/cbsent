import datetime

from cbsent.divergence import ScoredSentence, bank_level, divergence

UTC = datetime.timezone.utc


def _s(day, bank, score, topic="guidance"):
    return ScoredSentence(
        published_at=datetime.datetime(2025, 1, day, 14, 0, tzinfo=UTC),
        bank=bank, score=score, topic=topic,
    )


def test_future_text_is_never_used():
    sentences = [_s(10, "FED", 1.0), _s(20, "FED", -1.0)]
    asof = datetime.datetime(2025, 1, 15, tzinfo=UTC)
    # Only the 10th is visible, so the level is positive.
    assert bank_level(sentences, asof, "FED") > 0


def test_document_published_at_asof_is_excluded():
    ts = datetime.datetime(2025, 1, 10, 14, 0, tzinfo=UTC)
    sentences = [ScoredSentence(ts, "FED", 1.0, "guidance")]
    assert bank_level(sentences, ts, "FED") is None
    assert bank_level(sentences, ts + datetime.timedelta(seconds=1), "FED") == 1.0


def test_divergence_is_fed_minus_boc():
    sentences = [_s(10, "FED", 0.5), _s(10, "BOC", -0.5)]
    asof = datetime.datetime(2025, 1, 12, tzinfo=UTC)
    assert divergence(sentences, asof) == 1.0


def test_divergence_none_when_one_bank_missing():
    sentences = [_s(10, "FED", 0.5)]
    asof = datetime.datetime(2025, 1, 12, tzinfo=UTC)
    assert divergence(sentences, asof) is None


def test_recent_text_dominates_older_text():
    sentences = [_s(1, "FED", -1.0), _s(28, "FED", 1.0)]
    asof = datetime.datetime(2025, 2, 1, tzinfo=UTC)
    assert bank_level(sentences, asof, "FED") > 0


def test_zero_weight_topics_do_not_crash():
    sentences = [_s(10, "FED", 1.0, topic="unknown_topic")]
    asof = datetime.datetime(2025, 1, 12, tzinfo=UTC)
    assert bank_level(sentences, asof, "FED") == 1.0
