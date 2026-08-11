from cbsent.dictionary import classify, score


def test_inflation_pressure_is_hawkish():
    assert classify("Inflation remains elevated.") == "hawkish"


def test_rate_hike_is_hawkish():
    assert classify(
        "The Committee decided to raise the target range for the federal funds rate."
    ) == "hawkish"


def test_easing_is_dovish():
    assert classify("The Bank is maintaining its policy of quantitative easing.") == "dovish"


def test_weak_demand_is_dovish():
    assert classify("Demand has weakened and growth is slowing.") == "dovish"


def test_process_text_is_neutral():
    assert classify(
        "The Committee will continue to monitor the implications of incoming information."
    ) == "neutral"


def test_negation_blindness_is_preserved():
    # The published method does not handle negation; this failure mode is
    # exactly what the fine-tuned model is measured against, so the
    # baseline must keep it.
    assert classify("It is not yet appropriate to raise the target range.") == "hawkish"


def test_no_noun_no_modifier_score():
    assert score("The meeting was held in Washington on Tuesday and Wednesday.") == 0


def test_unemployment_does_not_match_employment():
    assert score("The unemployment rate edged up.") == 0
