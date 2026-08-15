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

## Domain-adaptive pretraining, ModernBERT-base (2026-08-14)

- command: `python scripts/pretrain_dapt.py --epochs 2` (final leg resumed
  with `--resume` from the step-2800 checkpoint after a battery-power stall)
- git commit: `6070027`
- corpus: 269,210 sentences / 2,354 documents, packed into 66,930 blocks
  of 128 tokens (8.6M tokens)
- training: bfloat16 on MPS, batch 32, lr 5e-5, 30% masking, 4,100 steps
  (2 epochs), linear warmup/decay; weights exported as float32

Validation MLM loss: 2.1210 before adaptation, 1.6064 after (24% lower).
The epoch-1 value (1.6066) from an earlier interrupted run of the same
seed reproduced to the third decimal on the restart, and the loss
plateaued during epoch 2, so two epochs saturate this corpus at this
scale.

Operational note: two stalls interrupted training, both traced to the
machine sleeping (an MPS command queue does not always survive
sleep/wake). Checkpointing every 400 steps plus --resume was added after
the first; the second cost 20 minutes instead of a full run.

## Reproducibility finding: pure-bf16 fine-tuning degrades accuracy (2026-08-15)

- git commit: `e473632`
- command: the same 2-epoch fine-tune of the adapted backbone on the TDW
  train split (identical seed, split, and batch order), varying only
  numeric precision and learning rate

| configuration | val weighted F1, epoch 1 | epoch 2 |
|---|---|---|
| MPS bf16, lr 2e-5 (first sweep run, 8 epochs, test set) | | 0.5122 |
| MPS bf16, lr 8e-5 | 0.5509 | 0.5735 |
| CPU fp32, lr 2e-5 | 0.5858 | 0.6595 |

bf16 was adopted for pretraining because fp32 ModernBERT is ~17x slower
on this machine's MPS (recorded above), and it was fine there: MLM val
loss matched the fp32 trajectory to three decimals. Fine-tuning is a
different regime: with only ~2,000 supervised sentences, pure-bf16
weights and optimizer state cost roughly 0.09 weighted F1 against fp32
at equal steps, and a 4x learning rate did not close the gap. The first
benchmark sweep was stopped after one run when its 0.5122 came in far
below the ~0.69 a RoBERTa-base baseline reaches on this benchmark.

Consequence: fine-tuning runs in fp32 on CPU (with per-batch dynamic
padding and linear warmup/decay added at the same time), while MLM
pretraining stays bf16 on MPS. The stopped run's number above is
retained but superseded.

## Addendum to the precision finding (2026-08-15)

- git commit: `975ab92`

Two further controlled 2-epoch runs complete the picture. Vanilla
ModernBERT-base (no domain adaptation) in bf16 scored 0.5622 at epoch 1
and then diverged to 0.0860 at epoch 2, so bf16 fine-tuning is unstable,
not merely lossy, and the adapted backbone was never the problem. fp16
with static loss scaling (scale 1024, skipping non-finite steps) reached
0.5641 / 0.6360 - stable and 6x faster than CPU, but still 0.024 weighted
F1 under fp32 at equal steps. With the evaluation target this close, the
sweep stays on fp32.

| configuration | epoch 1 | epoch 2 |
|---|---|---|
| CPU fp32 (reference) | 0.5858 | 0.6595 |
| MPS fp16 + loss scaling | 0.5641 | 0.6360 |
| MPS bf16, vanilla backbone | 0.5622 | 0.0860 (diverged) |

## TDW benchmark, first fp32 flagship run (2026-08-15)

- command: run 1 of `python scripts/benchmark_sweep.py` (fp32, cpu),
  backbone export/modernbert-cb-dapt, BoC extension 1,200 sentences
  (0 human-labelled), seed 20250811, 8 epochs, best epoch 5 by validation
- git commit: `40fa498` (run trained at 40fa498)

| metric | value |
|---|---|
| test weighted F1 | 0.6826 |
| test macro F1 | 0.6570 |
| test accuracy | 0.6855 |
| zero-shot GPT-5 on the same split (recorded above) | 0.7133 weighted F1 |

First honest read: the domain-adapted ModernBERT-base fine-tune lands in
the range the benchmark's authors reported for RoBERTa-base, and sits
3.1 weighted-F1 points below zero-shot GPT-5, not above it. The remaining
sweep runs measure seed spread and the BoC extension's effect;
ModernBERT-large domain adaptation is running as the next lever. A +9
margin over GPT-5 would require 0.80 weighted F1, above anything
published on this benchmark; that context stays attached to whatever the
final table shows.

## Negation probe (2026-08-15)

- command: `python scripts/negation_probe.py`
- git commit: `16354c4`
- probe: 24 hand-written minimal pairs in `data/negation_probe.csv`, labelled by the codebook rules cited per row, 10 of them carrying a negation cue
- inference device: cpu

| system | all items | negated items | non-negated items | distinct labels used on negated items |
|---|---|---|---|---|
| dictionary | 0.58 (14/24) | 0.20 (2/10) | 0.86 (12/14) | 3 (dovish, hawkish, neutral) |
| zero-shot gpt-5 | 1.00 (24/24) | 1.00 (10/10) | 1.00 (14/14) | 2 (dovish, hawkish) |
| fine-tune (export/bench-sweep/boc1200-20250811) | 0.62 (15/24) | 0.40 (4/10) | 0.79 (11/14) | 3 (dovish, hawkish, neutral) |

## 2-year yield study (2026-08-15)

- command: `python scripts/yield_study.py --model-dir export/bench-sweep/boc1200-20250811 --start 2011-01-01 --doc-types statement,minutes`
- git commit: `36d9af4`
- releases scored: 243 Fed (statement+minutes), 2011-01-01 onward
- yield: FRED DGS2 daily close, same-day change over prior business day, basis points
- score: mean P(hawkish)-P(dovish) over sentences, export/bench-sweep/boc1200-20250811, cpu

| relation | Pearson r | permutation p (two-sided) | n |
|---|---|---|---|
| score level vs same-day 2y move | +0.0136 | 0.8309 | 243 |
| score change vs same-day 2y move | +0.2105 | 0.0010 | 241 |

## Yield study by document type (2026-08-15)

- command: recomputed from `data/yield_study.csv` (same run as the entry
  above); subset by doc_type, computed after the pooled result was seen
  and reported for both types, not just the better one
- git commit: `36d9af4`

| subset | n | score-change vs same-day 2y move, Pearson r | permutation p |
|---|---|---|---|
| all releases | 241 | +0.2105 | 0.0010 |
| statements only | 126 | +0.2711 | 0.0027 |
| minutes only | 115 | +0.0831 | 0.3765 |

The signal lives in statements; minutes releases move yields far less
predictably, which is consistent with their content describing a meeting
three weeks past. The honest headline from this study is a statistically
significant but modest correlation, roughly 0.21 pooled or 0.27 on
statements, not anything near 0.5.

## Domain-adaptive pretraining, ModernBERT-large (2026-08-15)

- command: `python scripts/pretrain_dapt.py --backbone answerdotai/ModernBERT-large --epochs 1 --batch-size 16 --out export/modernbert-large-cb-dapt`
- git commit: `c494c1a`
- same corpus and packing as the base run (66,930 blocks, 8.6M tokens),
  bfloat16 on MPS, one epoch

Validation MLM loss: 1.7926 before adaptation, 1.2871 after. The large
model starts better on central bank text than the adapted base ended
(1.79 vs 1.61 unadapted-large vs adapted-base is not directly comparable
across capacities, but the 28% in-run drop is roughly double the base
model's per-epoch improvement), so the capacity is being used.

## Dictionary baseline on the TDW benchmark test split (2026-08-15)

- command: `python -c` over `cbsent.dictionary.classify` on
  data/benchmark/test.csv (the same 496 sentences the other systems see)
- git commit: `02b9d83`

| system | weighted F1 | macro F1 | accuracy |
|---|---|---|---|
| dictionary (Apel & Blix Grimaldi) | 0.5478 | 0.5156 | 0.5605 |
| cbsent fine-tune, 3-seed mean | 0.658 | | |
| zero-shot gpt-5 | 0.7133 | 0.7019 | 0.7137 |

Run so that all three systems have a number on the same benchmark split.
The fine-tune beats the dictionary by +11.0 weighted F1 and trails
zero-shot GPT-5 by -5.5.

## ModernBERT-large fine-tune preview, fp16 on MPS (2026-08-15)

- command: preview script in the session scratchpad, same data recipe as
  the flagship base run (TDW train + 1,200 BoC, seed 20250811), fp16 with
  static loss scaling, 6 epochs, test scored at each new validation peak
- git commit: `9f6fd74`
- purpose: decide whether a full fp32 large-model run is worth its cost

| epoch | val weighted F1 | non-finite steps skipped (of ~180) | test weighted F1 at val peak |
|---|---|---|---|
| 1 | 0.6546 | 34 | 0.5769 |
| 2 | 0.7282 | 43 | 0.6557 |
| 3 | 0.7051 | 33 | |
| 4 | 0.7126 | 55 | |
| 5 | 0.6956 | 77 | |
| 6 | 0.6902 | 101 | |

Best test score 0.6557, statistically indistinguishable from the base
model's 3-seed mean of 0.658 and still below zero-shot GPT-5 at 0.7133.
The skipped-step count climbing from 34 to 101 shows fp16 degrading as
training proceeds: by the last epoch more than half the updates were
discarded, so this preview is a floor on the large model rather than a
fair measurement of it. An fp32 run is therefore still worth its cost,
with the expectation of roughly 0.68 to 0.70 rather than a result that
overtakes the LLM.

## History rewrite to remove the weights blob (2026-08-15)

- command: `git-filter-repo --path export/cbsent/model.pt --invert-paths --force`
- git commit (post-rewrite HEAD at time of writing): `ae2b50d`

The 253 MB `export/cbsent/model.pt` had been committed five times before
`.gitignore` covered `export/`, putting five copies in the object store
and taking the repository to 1.6 GB. GitHub rejects any file over 100 MB,
so the repository could not be pushed at all.

That one path was removed from all 135 commits. Nothing else changed:
same commits, same messages, same order, same contents. The repository is
now 267 MB, of which the largest remaining items are the retired React
frontend's assets (11.8 MB) and the corpus snapshots
(`data/sentences.csv`, 10.8 MB across versions).

Every commit hash cited in the entries above therefore changed. The
complete old-to-new mapping for all 137 objects is committed as
`data/commit-map-pre-rewrite.txt`, so any hash quoted earlier in this
file can still be resolved to the commit that produced the number. Commit
messages and dates were untouched and are an independent way to locate
any entry's commit.

Model weights are distributed through the Hugging Face Hub
(`scripts/publish_hub.py`), which is where they belong; the accident was
committing them to git at all.

## Second rewrite: the stale LFS-tracked weights (2026-08-15)

- command: `git-filter-repo --path backend/analysis/model/export/model.pt --invert-paths --force`
- git commit (post-rewrite HEAD at time of writing): `db733b8`

The original project tracked its DistilBERT weights through Git LFS. That
backend was deleted when the dashboard was retired, but the LFS object
remained referenced by old commits, so pushing re-uploaded 266 MB against
a 1 GB free quota; the same quota exhaustion had previously broken the
project's CI.

Verified stale before removal: no LFS files in the working tree, no
`.gitattributes`, and one path ever tracked. After removal the repository
references zero LFS objects, and the stale local LFS cache was deleted.

The repository is now 13 MB, down from 1.6 GB, across the same 136
commits. `data/commit-map-pre-rewrite.txt` has been regenerated to map
hashes from this rewrite as well.
