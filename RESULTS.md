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

## Stance macro-F1, held-out 2025-08-01 to 2026-08-01 (2026-08-11)

- command: `python scripts/eval.py --cut-date 2025-08-01 --eval-end 2026-08-01 --allow-bootstrap`
- git commit: `52516cb`
- eval sentences: 595 (0/595 human-verified)
- label provenance: includes bootstrap labels

| system | macro-F1 | hawkish F1 | dovish F1 | neutral F1 |
|---|---|---|---|---|
| dictionary | 0.5794 | 0.4903 | 0.4217 | 0.8262 |
| zero-shot gpt-5 | 0.8208 | 0.7863 | 0.7615 | 0.9146 |
| cbsent (fine-tuned) | 0.6804 | 0.5429 | 0.6114 | 0.8868 |

PROVISIONAL. 595 of 595 reference labels come from the gpt-5-mini bootstrap pass rather than a human. Two of the three systems are therefore partly measured against themselves: the zero-shot baseline shares a model family and prompt with the labeller, and the fine-tuned model was trained on those labels. Read the zero-shot row as an upper bound inflated by that overlap, not as accuracy. The headline comparison is the margin over the dictionary baseline, which shares nothing with the labeller. This table becomes a headline result only when the held-out labels are human-verified.

## Stance macro-F1, dictionary and LLM agreement subset, held-out 2025-08-01 to 2026-08-01 (2026-08-11)

- command: `python scripts/eval.py --cut-date 2025-08-01 --eval-end 2026-08-01 --allow-bootstrap --consensus-only`
- git commit: `52516cb`
- eval sentences: 432 (0/432 human-verified)
- label provenance: includes bootstrap labels

| system | macro-F1 | hawkish F1 | dovish F1 | neutral F1 |
|---|---|---|---|---|
| dictionary | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| zero-shot gpt-5 | 0.8598 | 0.9091 | 0.7143 | 0.9559 |
| cbsent (fine-tuned) | 0.6839 | 0.5977 | 0.5432 | 0.9109 |

PROVISIONAL. 432 of 432 reference labels come from the gpt-5-mini bootstrap pass rather than a human. Two of the three systems are therefore partly measured against themselves: the zero-shot baseline shares a model family and prompt with the labeller, and the fine-tuned model was trained on those labels. Read the zero-shot row as an upper bound inflated by that overlap, not as accuracy. The headline comparison is the margin over the dictionary baseline, which shares nothing with the labeller. This table becomes a headline result only when the held-out labels are human-verified.

## Correction: the agreement-subset table above is invalid (2026-08-11)

- git commit: `52516cb`

The "dictionary and LLM agreement subset" table immediately above must not
be used. Restricting to sentences where the dictionary and the LLM agree
makes the reference label identical to the dictionary's own prediction on
every row in the subset, so the dictionary scores 1.0000 by construction
and the other two systems are measured against a baseline that cannot
lose. The subset is circular, not stricter.

The `--consensus-only` option that produced it has been removed from
`scripts/eval.py` so the table cannot be regenerated. The entry is left
in place because this file is append-only. The valid provisional table is
the one before it, and the only fix for its label provenance is
human review, not a cleverer subset.

## Reproducibility finding: MPS inference is not deterministic (2026-08-11)

- git commit: `52516cb`
- command: scoring the 595 held-out sentences three times with one loaded
  model, first on `mps` and then on `cpu`, comparing predicted stance
  label counts across repeats

Scoring identical input with identical weights on Apple MPS returned
different predictions between repeats: 79 of 595 sentences changed label
between run 1 and run 2, and 23 of 595 between run 1 and run 3. On CPU the
same comparison gave 0 of 595 both times. Batch size was not the cause;
scoring at batch 64 and batch 16 agreed exactly on both devices.

Effect on reported numbers: the same evaluation could swing by roughly two
macro-F1 points between runs on MPS (0.6559 to 0.6804 observed). Every
script that reports a number therefore takes `--device` and defaults to
`cpu`; three consecutive CPU runs of `scripts/eval.py` return
0.6804 macro-F1 exactly. Training still runs on MPS, where the
nondeterminism only perturbs the optimisation path and the resulting
weights are committed as an artefact.

The provisional table above was produced before this default changed. Its
cbsent row happens to equal the deterministic CPU value, and the entry
below re-runs it CPU-pinned so a reproducible entry exists.

## Stance macro-F1, held-out 2025-08-01 to 2026-08-01 (2026-08-11)

- command: `python scripts/eval.py --cut-date 2025-08-01 --eval-end 2026-08-01 --allow-bootstrap`
- git commit: `52516cb`
- eval sentences: 595 (0/595 human-verified)
- inference device: cpu
- label provenance: includes bootstrap labels

| system | macro-F1 | hawkish F1 | dovish F1 | neutral F1 |
|---|---|---|---|---|
| dictionary | 0.5794 | 0.4903 | 0.4217 | 0.8262 |
| zero-shot gpt-5 | 0.8208 | 0.7863 | 0.7615 | 0.9146 |
| cbsent (fine-tuned) | 0.6804 | 0.5429 | 0.6114 | 0.8868 |

PROVISIONAL. 595 of 595 reference labels come from the gpt-5-mini bootstrap pass rather than a human. Two of the three systems are therefore partly measured against themselves: the zero-shot baseline shares a model family and prompt with the labeller, and the fine-tuned model was trained on those labels. Read the zero-shot row as an upper bound inflated by that overlap, not as accuracy. The headline comparison is the margin over the dictionary baseline, which shares nothing with the labeller. This table becomes a headline result only when the held-out labels are human-verified.

## Negation/hedge ablation, held-out 2025-08-01 to 2026-08-01 (2026-08-11)

- command: `python scripts/ablation.py --cut-date 2025-08-01 --eval-end 2026-08-01 --allow-bootstrap`
- git commit: `1093f25`
- eval sentences: 595, of which 168 contain a cue
- inference device: cpu

| variant | macro-F1 (all) | macro-F1 (cue sentences) |
|---|---|---|
| with negation markers | 0.6804 | 0.7257 |
| without negation markers | 0.6281 | 0.7093 |

Effect of cue marking: +0.0522 macro-F1 overall, +0.0163 on cue sentences.

## Event study, 2025-08-01 to 2026-08-01 (2026-08-11)

- command: `python scripts/event_study.py --eval-start 2025-08-01 --eval-end 2026-08-01 --horizon-minutes 60`
- git commit: `dcfac41`
- scheduled decisions in window: 16
- inference device: cpu
- decisions with index and FX data: 15
- consensus surprises: 0
- FX alignment basis: daily, intraday
- horizon after release: 60 minutes (intraday) or next available daily rate
- result: no consensus surprises occurred in this window: every scheduled decision matched the economist consensus recorded in data/decisions.csv. Across all 15 scheduled decisions, the index moved directionally ahead of the pair on 9 of 15.
