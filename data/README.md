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

## raw/, fx_cache/, llm_cache/

Fetch caches, not committed. `raw/` holds scraped pages and the BoC
announcement-date probe index, `fx_cache/` Dukascopy ticks and Valet
daily rates, `llm_cache/` one JSON file per LLM label keyed by model and
sentence so no sentence is ever billed twice.
