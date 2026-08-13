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

## Event study, 2025-08-01 to 2026-08-01 (2026-08-11)

- command: `python scripts/event_study.py --eval-start 2025-08-01 --eval-end 2026-08-01 --horizon-minutes 60`
- git commit: `e85df07`
- scheduled decisions in window: 16
- inference device: cpu
- decisions with index and FX data: 15
- consensus surprises: 0
- FX alignment basis: intraday
- horizon after release: 60 minutes (intraday) or next available daily rate
- result: no consensus surprises occurred in this window: every scheduled decision matched the economist consensus recorded in data/decisions.csv. Across all 15 scheduled decisions, the index moved directionally ahead of the pair on 9 of 15 (two-sided binomial p = 0.607 against a fair coin, not distinguishable from chance).

## Inference cost and speed (2026-08-11)

- command: `python scripts/cost_compare.py --sample 40 --input-price 1.25 --output-price 10.0 --price-source https://developers.openai.com/api/docs/pricing`
- git commit: `fac5165`
- prices used: $1.25 per million input tokens, $10.0 per million output tokens, from https://developers.openai.com/api/docs/pricing
- token counts are real API usage over 39 uncached sentences and include reasoning tokens, which are billed but absent from the response text

| system | throughput | tokens per sentence | marginal cost per 1,000 sentences |
|---|---|---|---|
| cbsent (fine-tuned, local) | 122.0 sentences/s on cpu | n/a | $0.00 |
| zero-shot gpt-5 | 1.8 sentences/s at 8 workers | 367 in + 200 out | $2.46 |

## Negation probe (2026-08-11)

- command: `python scripts/negation_probe.py`
- git commit: `330d6eb`
- probe: 24 hand-written minimal pairs in `data/negation_probe.csv`, labelled by the codebook rules cited per row, 10 of them carrying a negation cue
- inference device: cpu

| system | all items | negated items | non-negated items | distinct labels used on negated items |
|---|---|---|---|---|
| dictionary | 0.58 (14/24) | 0.20 (2/10) | 0.86 (12/14) | 3 (dovish, hawkish, neutral) |
| zero-shot gpt-5 | 1.00 (24/24) | 1.00 (10/10) | 1.00 (14/14) | 2 (dovish, hawkish) |
| cbsent (fine-tuned) | 0.67 (16/24) | 0.60 (6/10) | 0.71 (10/14) | 1 (hawkish) |

cbsent (fine-tuned) answered `hawkish` for every one of the 10 negated items. Its score on that subset is therefore the label mix of the subset and carries no evidence of negation sensitivity.

## Negation/hedge ablation across seeds, held-out 2025-08-01 to 2026-08-01 (2026-08-11)

- command: `python scripts/ablation_sweep.py --seeds 20250811 7 1234 --epochs 6 --allow-bootstrap`
- git commit: `b2feb9a`
- eval sentences: 595, of which 168 contain a cue
- inference device: cpu, training device: mps

| variant | macro-F1 mean over 3 seeds | sd | cue-sentence macro-F1 mean | sd |
|---|---|---|---|---|
| with negation markers | 0.6254 | 0.0033 | 0.7015 | 0.0086 |
| without negation markers | 0.6274 | 0.0184 | 0.7238 | 0.0145 |

Effect of cue marking: -0.0020 macro-F1 overall and -0.0224 on cue sentences. The effect is smaller than the between-seed spread, so this corpus cannot distinguish the transform's effect from training noise.

## The multi-seed ablation supersedes the single-run ablation (2026-08-11)

- git commit: `93e1b41`

The single-run entry earlier in this file reported cue marking worth
+0.0522 macro-F1. That number came from one training run per variant and
does not survive repetition. Across three seeds per variant the effect is
-0.0020 macro-F1 overall and -0.0224 on cue sentences, with a
between-seed spread of 0.0033 to 0.0184, so the transform provides no
measurable benefit on this corpus and the earlier figure was training
noise read as signal.

Use the multi-seed table. The single-run entry is retained because this
file is append-only, and `make ablate` now runs the seed sweep;
`make ablate-single` reproduces the superseded one-run version.

This is consistent with the negation probe result recorded above: the
model does not read negation scope, so an input transform whose only
purpose is to expose that scope has nothing to contribute. The bottleneck
is the training signal, not the encoding.

## Headline verdict: the fine-tune does not beat the LLM baseline (2026-08-11)

- git commit: `18611ae`
- based on the CPU-pinned three-way table, the negation probe, the
  multi-seed ablation, and the cost measurement, all recorded above

On the held-out year 2025-08-01 to 2026-08-01 the fine-tuned model reaches
0.6804 stance macro-F1 against 0.8208 for zero-shot GPT-5 and 0.5794 for
the dictionary method. The fine-tune loses to the LLM by 0.140 macro-F1.

What was tried before writing this down: class weighting from the training
window only, an epoch budget chosen by chronological validation rather
than picked by hand (14 epochs, best checkpoint at epoch 12, validation
peaking there), and the negation/hedge input transform, which the seed
sweep then showed to be worth nothing.

What was deliberately not tried: tuning further against this target. The
reference labels are gpt-5-mini's, so "beat GPT-5" currently means "agree
with gpt-5-mini's opinions better than GPT-5 does", and GPT-5 shares a
model family and a prompt with the labeller. Optimising that gap harder
would be optimising a circular metric, and any win would evaporate the
moment real labels arrived. The honest move is to get human labels on the
held-out year first; the review queue is built and prioritised for that.

The honest alternative claim, as of this commit:

| claim | value |
|---|---|
| margin over the dictionary baseline | +0.1010 macro-F1 (0.6804 vs 0.5794) |
| margin over zero-shot GPT-5 | -0.1404 macro-F1 (0.6804 vs 0.8208) |
| local throughput | 122.0 sentences/second on CPU |
| marginal cost, 1,000 sentences, local | $0.00 |
| marginal cost, 1,000 sentences, GPT-5 | $2.46 |
| negation minimal pairs, 10 negated items | cbsent 0.60 with one label used, GPT-5 1.00 |

So the defensible position is a cheap, local, reproducible scorer that
clearly beats the literature's dictionary method and clearly loses to a
frontier LLM, and that does not yet read negation. It is not a
state-of-the-art claim and this file should not be read as making one.

## Negation probe (2026-08-11)

- command: `python scripts/negation_probe.py`
- git commit: `c74ccd4`
- probe: 24 hand-written minimal pairs in `data/negation_probe.csv`, labelled by the codebook rules cited per row, 10 of them carrying a negation cue
- inference device: cpu

| system | all items | negated items | non-negated items | distinct labels used on negated items |
|---|---|---|---|---|
| dictionary | 0.58 (14/24) | 0.20 (2/10) | 0.86 (12/14) | 3 (dovish, hawkish, neutral) |
| zero-shot gpt-5 | 1.00 (24/24) | 1.00 (10/10) | 1.00 (14/14) | 2 (dovish, hawkish) |
| cbsent (fine-tuned) | 0.67 (16/24) | 0.60 (6/10) | 0.71 (10/14) | 1 (hawkish) |

cbsent (fine-tuned) answered `hawkish` for every one of the 10 negated items. Its score on that subset is therefore the label mix of the subset and carries no evidence of negation sensitivity.

## Stance macro-F1, held-out 2025-08-01 to 2026-08-01 (2026-08-11)

- command: `python scripts/eval.py --cut-date 2025-08-01 --eval-end 2026-08-01 --allow-bootstrap`
- git commit: `c74ccd4`
- eval sentences: 595 (0/595 human-verified)
- inference device: cpu
- label provenance: includes bootstrap labels

| system | macro-F1 | hawkish F1 | dovish F1 | neutral F1 |
|---|---|---|---|---|
| dictionary | 0.5794 | 0.4903 | 0.4217 | 0.8262 |
| zero-shot gpt-5 | 0.8208 | 0.7863 | 0.7615 | 0.9146 |
| cbsent (fine-tuned) | 0.6804 | 0.5429 | 0.6114 | 0.8868 |

PROVISIONAL. 595 of 595 reference labels come from the gpt-5-mini bootstrap pass rather than a human. Two of the three systems are therefore partly measured against themselves: the zero-shot baseline shares a model family and prompt with the labeller, and the fine-tuned model was trained on those labels. Read the zero-shot row as an upper bound inflated by that overlap, not as accuracy. The headline comparison is the margin over the dictionary baseline, which shares nothing with the labeller. This table becomes a headline result only when the held-out labels are human-verified.

## Repository hygiene note: a weights blob is in history (2026-08-11)

- git commit: `d780135`

The 254 MB `export/cbsent/model.pt` was tracked by accident between
commits `ea1f2b5` and `52516cb` before `.gitignore` covered
`export/`, and was re-committed several times, so the object store holds
several copies and `.git` is about 1.6 GB. It is untracked from this
commit on, and `export/` is ignored.

The blob is still reachable from those earlier commits. Purging it needs a
history rewrite, which would change every commit hash this file cites and
so break the audit trail that is the point of this file. That trade is the
repository owner's to make, not something to do silently; the numbers above
remain checkable against the hashes as recorded.

Weights are distributed through the Hugging Face Hub, per
`scripts/publish_hub.py`, and are not intended to live in git.

## Zero-shot gpt-5 on the TDW benchmark test split (2026-08-12)

- command: `python scripts/gpt5_benchmark.py --model gpt-5`
- git commit: `01735dd`
- prompt: benchmark label definitions, stance only, cached
- test sentences: 496, invalid responses: 0

| metric | value |
|---|---|
| weighted F1 (benchmark standard) | 0.7133 |
| macro F1 | 0.7019 |
| accuracy | 0.7137 |

## Stance macro-F1, held-out 2025-08-01 to 2026-08-01 (2026-08-12)

- command: `python scripts/eval.py --cut-date 2025-08-01 --eval-end 2026-08-01 --allow-bootstrap`
- git commit: `aa5f844`
- eval sentences: 601 (0/601 human-verified)
- inference device: cpu
- label provenance: includes bootstrap labels

| system | macro-F1 | hawkish F1 | dovish F1 | neutral F1 |
|---|---|---|---|---|
| dictionary | 0.5796 | 0.4872 | 0.4260 | 0.8255 |
| zero-shot gpt-5 | 0.8196 | 0.7863 | 0.7580 | 0.9145 |
| cbsent (fine-tuned) | 0.6770 | 0.5390 | 0.6051 | 0.8868 |

PROVISIONAL. 601 of 601 reference labels come from the gpt-5-mini bootstrap pass rather than a human. Two of the three systems are therefore partly measured against themselves: the zero-shot baseline shares a model family and prompt with the labeller, and the fine-tuned model was trained on those labels. Read the zero-shot row as an upper bound inflated by that overlap, not as accuracy. The headline comparison is the margin over the dictionary baseline, which shares nothing with the labeller. This table becomes a headline result only when the held-out labels are human-verified.

## Corpus expansion for domain adaptation (2026-08-12)

- commands: `python scripts/ingest_expanded.py` then
  `python scripts/ingest_expanded.py --sources boc` then
  `python scripts/ingest.py --earliest 2015-01-01`
- git commit: `2c1693e`

| source | documents |
|---|---|
| Fed speeches (official JSON feed, 2006-2026, exact datetimes) | 1,326 |
| Fed testimony (official JSON feed) | 278 |
| FOMC minutes (incl. archive pages to 2011) | 116 |
| FOMC statements (incl. archive pages to 2011) | 128 |
| BoC rate announcements (fixed announcement dates to 2015) | 93 |
| BoC speeches (paged RSS feed; the listing page is JS-only) | 413 |
| total | 2,354 |

Sentences in the corpus: 269,210. Notes recorded rather than absorbed:
283 BoC speech pages failed extraction (no post-content body or under 500
characters, typically PDF-only pages); statement release times before
March 2013 are stamped 2:15 p.m. ET without distinguishing the 12:30
press-conference meetings of 2011-2012, which nothing downstream reads at
intraday resolution; BoC speeches carry no clock time and are stamped
11:59 p.m. ET so point-in-time queries can never see them early.

Fed statement+minutes releases since 2011-01-01: 244, which is the
candidate set for the yield study.

## Reproducibility finding: fp32 ModernBERT is pathologically slow on MPS (2026-08-13)

- git commit: `26d1e72`
- command: single AdamW training steps of ModernBERT-base at batch 32,
  sequence length 128, timed after one warmup step on the same tensors

| configuration | seconds per step |
|---|---|
| MPS, float32 | ~50 (0.02 it/s observed over 600 steps) |
| MPS, autocast bf16 over fp32 weights | 25.6 |
| CPU, float32, 8 threads | 6.9 |
| MPS, pure bfloat16 | 2.9 |

Full-precision ModernBERT on this machine's MPS backend is ~17x slower
than pure bfloat16; short sequences (as in the initial smoke test) do not
trigger the slow path, which is why it was not caught before launch. The
first pretraining launch was killed at step 600 of 4,100 with a 52-hour
ETA. Domain-adaptive pretraining therefore runs in bfloat16 end to end
(losses finite and decreasing; float16 produced NaN without loss scaling)
and the adapted weights are exported as float32.
