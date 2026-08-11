# RESULTS

Append-only log of every reported number. Each entry records the command
that produced it, the git commit it ran at, and the date it ran. Numbers
that do not appear here do not exist.

---

## Corpus, Phase 1 (2026-08-11)

- command: `python scripts/ingest.py && python scripts/export_snapshot.py`
- git commit: `c702ec6`

| source | documents | sentences | first release | last release |
|---|---|---|---|---|
| FOMC statements | 40 | | 2021-09-22 | 2026-07-29 |
| FOMC minutes | 39 | | 2021-10-13 | 2026-07-08 |
| BoC rate announcements | 40 | | 2021-09-08 | 2026-07-15 |
| total | 119 | 11868 | | |

Coverage check: the Bank of Canada holds eight fixed announcement dates
per year and the corpus contains exactly eight for each of 2022, 2023,
2024 and 2025. The FOMC holds eight meetings per year and the corpus
contains eight statements for each full year.

Release timestamps: all 79 Fed documents are stamped 14:00 ET. Of the 40
BoC announcements, 19 are stamped 10:00 ET (every announcement through
2023) and 21 are stamped 09:45 ET (every announcement from 2024-01-24),
matching the Bank's December 2023 change to its communication schedule.

Held-out window: 2025-08-01 to 2026-08-01, containing 16 scheduled rate
decisions (8 Fed, 8 BoC). Training window: 2021-08-01 to 2025-08-01.

## Bootstrap labels, Phase 2 (2026-08-11)

- command: `python scripts/bootstrap_labels.py --workers 32`
- git commit: `c07166a`
- selection: all 2,385 sentences from Fed statements and BoC rate
  announcements plus a seeded per-document sample of FOMC minutes,
  2,980 sentences total (2,385 in the training window, 595 in the
  held-out window)
- labellers: the dictionary method (negation-blind by construction) and
  gpt-5-mini prompted with the codebook definitions, 0 responses invalid

Stance distribution of the two bootstrap passes:

| stance | dictionary | gpt-5-mini |
|---|---|---|
| neutral | 2033 | 1853 |
| hawkish | 648 | 676 |
| dovish | 299 | 451 |

Dictionary and LLM agree on stance for 2,025 of 2,980 sentences (68.0%),
leaving 955 disagreements. The largest disagreement cells are sentences
the dictionary calls neutral and the LLM calls directional (275 hawkish,
249 dovish) and sentences the dictionary calls hawkish that the LLM calls
neutral (230). 87 sentences are labelled in opposite directions.

These are bootstrap labels, not ground truth. No human labels exist yet,
so no evaluation number in this file may be read as a headline result
until the review queue below is worked through.

Review queue built by `python labeling/review_html.py`: 1,757 sentences
in priority order, being all 595 held-out-window sentences, then 792
dictionary/LLM disagreements in the training window, then a 370-sentence
stratified sample of agreements (15 per bank x year x stance cell).
