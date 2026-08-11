from cbsent.negation import HEDGE_TOKEN, NEG_TOKEN, mark_cues


def test_negation_cue_marked():
    out = mark_cues("It is not yet appropriate to raise the target range.")
    assert NEG_TOKEN in out
    assert "not yet" in out


def test_hedge_cue_marked():
    out = mark_cues("Some further policy firming may be appropriate.")
    assert HEDGE_TOKEN in out
    assert "may" in out


def test_sentence_without_cues_is_unchanged():
    text = "Inflation remains elevated."
    assert mark_cues(text) == text


def test_original_words_are_preserved():
    text = "The Committee does not anticipate reducing the policy rate."
    out = mark_cues(text)
    stripped = out.replace(NEG_TOKEN + " ", "").replace(HEDGE_TOKEN + " ", "")
    assert stripped == text


def test_cue_inside_word_is_not_marked():
    # "cannot" is a cue, but "notable" and "another" are not.
    out = mark_cues("A notable decline occurred in another sector.")
    assert NEG_TOKEN not in out
