# data/

Committed inputs and snapshots. Everything here is either scraped by
`scripts/ingest.py`, exported by `scripts/export_snapshot.py`, or
hand-assembled with a cited source per row.

## decisions.csv

Every scheduled Fed and Bank of Canada rate decision in the held-out
window, with the delivered move and the economist consensus going in.

| column | meaning |
|---|---|
| `bank` | FED or BOC |
| `decision_date` | announcement date |
| `release_ts_utc` | release instant in UTC (FOMC 2:00 p.m. ET, BoC 9:45 a.m. ET) |
| `actual_bps` | delivered change in basis points |
| `consensus_bps` | consensus change in basis points, blank if not verifiable |
| `is_surprise` | yes when the delivered move differed from consensus |
| `consensus_source` | URL supporting the consensus figure |
| `note` | what that source says |

Consensus is the economist consensus reported in press coverage at the
time, not a market-implied expectation from OIS or futures, which has no
free historical source. Rows whose consensus could not be sourced are
left blank and are excluded from the surprise count rather than guessed.

Delivered moves were cross-checked against the official rate series:
FRED `DFEDTARU` for the Fed target range upper bound, and Bank of Canada
Valet series `V39079` for the overnight rate target.

## documents.csv, sentences.csv

Corpus snapshots. `published_at` is the exact release timestamp and is
carried on both tables so point-in-time queries need no join.

## event_study.csv

Written by `scripts/event_study.py`: the index level, its change since
the previous decision, and the USD/CAD move after each release.

## llm_labels.csv

Every label either LLM produced, one row per (model, sentence), with the
token usage that was billed for it. Written by
`scripts/export_llm_labels.py` from the request cache.

This file is what makes the evaluation table verifiable without an
OpenAI account: `scripts/eval.py` primes from it before making any
request, so running `make eval` with no API key still reproduces the
zero-shot baseline row exactly. Deleting it is safe but then reproducing
that row costs API calls.

## raw/, fx_cache/, llm_cache/, score_cache.json

Fetch caches, not committed. `raw/` holds scraped pages and the BoC
announcement-date probe index, `fx_cache/` Dukascopy ticks and Valet
daily rates, `llm_cache/` one JSON file per LLM request keyed by model and
prompt so no sentence is ever billed twice, and `score_cache.json` the
model's own sentence scores so the event study can be re-run without
rescoring the corpus.
