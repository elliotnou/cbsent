from cbsent.segment import segment_sentences


def test_basic_split():
    text = "Inflation remains elevated. The Committee seeks maximum employment."
    assert segment_sentences(text) == [
        "Inflation remains elevated.",
        "The Committee seeks maximum employment.",
    ]


def test_abbreviations_do_not_split():
    text = "Growth of 2.5 per cent is expected by the U.S. authorities according to Mr. Powell."
    assert len(segment_sentences(text)) == 1


def test_decimal_numbers_do_not_split():
    text = "The target range was raised to 5.25 percent from 5.00 percent at the previous meeting."
    assert len(segment_sentences(text)) == 1


def test_long_semicolon_clauses_split():
    text = (
        "Job gains have been robust in recent months, and the unemployment rate has remained low; "
        "inflation remains elevated, reflecting supply and demand imbalances related to the pandemic."
    )
    result = segment_sentences(text)
    assert len(result) == 2


def test_short_semicolon_stays_together():
    text = "The vote was taken under sections 2, 5; 7, 12 of the Federal Reserve Act as amended."
    assert len(segment_sentences(text)) == 1


def test_enumerated_clauses_split():
    text = (
        "The Committee agreed that it would be appropriate to consider several factors: "
        "(1) the cumulative tightening of monetary policy since early in the year was substantial; "
        "(2) the lags with which monetary policy affects economic activity and inflation remained long; "
        "and (3) financial conditions had tightened considerably over recent months."
    )
    result = segment_sentences(text)
    assert len(result) == 3
    assert not any(s.startswith("(") for s in result)


def test_short_fragments_dropped():
    text = "Page 4. The Committee decided to maintain the target range at its current level."
    assert segment_sentences(text) == [
        "The Committee decided to maintain the target range at its current level."
    ]


def test_empty_input():
    assert segment_sentences("") == []
    assert segment_sentences("   \n ") == []
