"""End-to-end scorer checks. Skipped when no trained model is present."""

import os

import pytest

torch = pytest.importorskip("torch")

MODEL_DIR = "export/cbsent"

pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(MODEL_DIR, "model.pt")),
    reason="no trained model in export/cbsent",
)


@pytest.fixture(scope="module")
def scorer():
    from cbsent.model import Scorer
    return Scorer(MODEL_DIR)


def test_scores_are_in_range(scorer):
    out = scorer.score_sentences([
        "Inflation remains elevated and the labour market is tight.",
        "Economic growth has slowed and demand has weakened materially.",
    ])
    assert len(out) == 2
    for r in out:
        assert -1.0 <= r["score"] <= 1.0
        assert r["stance"] in ("hawkish", "dovish", "neutral")


def test_batching_matches_single_pass(scorer):
    sentences = [
        "Inflation remains elevated.",
        "The Committee decided to maintain the target range.",
        "Growth has slowed and slack has increased.",
        "The labour market remains tight.",
        "Members agreed to continue reducing the balance sheet.",
    ]
    one_batch = scorer.score_sentences(sentences, batch_size=64)
    many_batches = scorer.score_sentences(sentences, batch_size=2)
    assert [r["stance"] for r in one_batch] == [r["stance"] for r in many_batches]
    for a, b in zip(one_batch, many_batches):
        assert abs(a["score"] - b["score"]) < 1e-3


def test_empty_input(scorer):
    assert scorer.score_sentences([]) == []


def test_document_api_returns_aggregate():
    from cbsent import score
    out = score(
        "Inflation remains elevated. The Committee decided to raise the "
        "target range for the federal funds rate by 25 basis points.",
        model_dir=MODEL_DIR,
    )
    assert set(out) == {"score", "stance", "n_sentences", "sentences"}
    assert out["n_sentences"] == 2
    assert -1.0 <= out["score"] <= 1.0
