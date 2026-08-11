from cbsent.labels import DEFAULT_TOPIC_WEIGHT, STANCES, TOPIC_WEIGHTS, TOPICS


def test_stance_vocabulary_is_three_class():
    assert set(STANCES) == {"hawkish", "dovish", "neutral"}


def test_every_topic_has_a_weight():
    assert set(TOPIC_WEIGHTS) == set(TOPICS)


def test_weights_are_in_unit_range():
    assert all(0.0 <= w <= 1.0 for w in TOPIC_WEIGHTS.values())
    assert 0.0 <= DEFAULT_TOPIC_WEIGHT <= 1.0


def test_policy_topics_carry_full_weight():
    assert TOPIC_WEIGHTS["guidance"] == 1.0
    assert TOPIC_WEIGHTS["inflation"] == 1.0
