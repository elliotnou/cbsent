# cbsent

Central bank tone engine. Scores Federal Reserve and Bank of Canada
communications for hawkish/dovish stance at the sentence level, evaluated
against a published benchmark, the literature's dictionary method, and
zero-shot GPT-5, and validated point-in-time against the 2-year Treasury
market.

A library, not a hosted app: an importable package, a CLI, and scripts
that reproduce every number in [RESULTS.md](RESULTS.md).

## Install

```bash
pip install -e ".[model]"      # scoring
pip install -e ".[research]"   # scoring plus everything RESULTS.md needs
```

## Use

```bash
$ cbsent score "Inflation remains elevated and the labour market is tight."
score:  +1.0000   (up)
stance: hawkish
sentences scored: 1

$ cbsent score "Economic growth has slowed and slack has increased."
score:  -0.1967   (down)
stance: dovish
```

Scores are `P(hawkish) - P(dovish)`, so they run from -1 to +1 and 0 means
no directional signal. Whole documents get segmented, scored per sentence,
and aggregated, with the breakdown available so a reader can audit the
verdict rather than trust it:

```bash
$ cbsent score -f fomc_statement.txt --sentences
score:  +0.7101   (up)
stance: hawkish
sentences scored: 5

  +0.998  hawk    Recent indicators suggest that economic activity has continued to...
  +0.998  hawk    Job gains have been robust in recent months, and the unemployment...
  +0.583  hawk    Inflation remains elevated.
  +0.971  hawk    The Committee decided to raise the target range for the federal f...
  +0.000  neut    In assessing the appropriate stance of monetary policy, the Commi...
```

Also `cbsent score -f -` to read stdin, `--json` for machine-readable
output, and in Python:

```python
from cbsent import score
result = score(open("boc_announcement.txt").read())
print(result["score"], result["stance"])
```

## What it is

```
official sites        release timestamps      domain adaptation      task
-------------         -----------------       -----------------      ----
FOMC statements  -->  documents table    -->  ModernBERT MLM    -->  stance
FOMC minutes          (published_at)          on 269k sentences      3-class
Fed speeches     -->  sentences table         8.6M tokens            + topic
BoC announcements     (published_at)                                 (legacy head)
BoC speeches
```

**Corpus.** 2,354 documents, 269,210 sentences: FOMC statements and
minutes back to 2011, 1,326 Fed speeches and 278 testimony appearances
from the official feeds, Bank of Canada rate announcements and 413
speeches. Every document carries its exact release timestamp (FOMC 2:00
p.m. ET, 2:15 p.m. before March 2013; BoC 9:45 a.m. ET, 10:00 a.m. before
2024-01-24) and every sentence row denormalizes it, so a point-in-time
query cannot see the future without violating the schema.

**Segmentation** is tuned to central bank prose: decimal rates, dotted
abbreviations, enumerated clauses in minutes, and semicolon-chained
sentences that each carry their own stance.

**Two model tracks.** A multi-task DistilBERT (stance + topic) trained on
this project's own labels and evaluated on a chronologically held-out
year, and a ModernBERT domain-adapted on the unlabelled corpus then
fine-tuned on the public FOMC benchmark. The second is the better scorer
and is what the CLI loads by default.

## What it shows

All three systems on the benchmark's held-out test split (496 sentences,
human-annotated by its authors):

| system | weighted F1 |
|---|---|
| dictionary method (Apel & Blix Grimaldi) | 0.5478 |
| **cbsent fine-tune, 3-seed mean** | **0.658** |
| zero-shot GPT-5 | 0.7133 |

The fine-tune beats the literature's dictionary method by **+11 F1** and
trails zero-shot GPT-5 by **5.5**. It is not state of the art and this
repository does not claim to be; for context, the benchmark's own authors
reported roughly 0.71 with RoBERTa-large.

What it buys instead, measured: **122 sentences/second** locally at **zero
marginal cost**, against ~1.8/second and **$2.46 per 1,000 sentences**
through the API. Scoring this corpus once costs about $660 and 41 hours
via GPT-5, or 37 minutes and nothing locally. Inference is CPU-pinned and
bit-exact across runs, so a number reported today reproduces in three
years, which an API model cannot promise.

**Market validation.** Document tone changes track same-day 2-year
Treasury yield moves across 243 Fed releases since 2011, computed
point-in-time from text published before each release:

| subset | n | Pearson r | permutation p |
|---|---|---|---|
| all releases | 241 | +0.2105 | 0.0010 |
| statements only | 126 | +0.2711 | 0.0027 |
| minutes only | 115 | +0.0831 | 0.3765 |

Significant but modest, and concentrated in statements. Minutes describe a
meeting three weeks past and move yields far less predictably.

## What it does not show

Kept here deliberately, because a repository that only reports its wins is
not evidence of anything.

- **Negation is handled poorly.** On a 24-item minimal-pair probe the
  fine-tune gets 4 of 10 negated sentences right; GPT-5 gets 10 of 10, the
  dictionary 2. An inline negation-marking transform was built to fix
  this, then measured across seeds at **-0.002 F1** and abandoned. A
  single-run measurement had suggested +0.052 before the seed sweep
  showed it was noise.
- **The FX event study is null.** Every scheduled decision in the held-out
  year matched economist consensus, so there were no surprises to test.
  Across all 15 decisions the divergence index moved with USD/CAD on 9,
  which a binomial test cannot separate from a coin flip (p = 0.607).
- **The held-out-year evaluation is provisional.** Its reference labels
  come from an LLM bootstrap, so the GPT-5 row there is inflated by shared
  model family and prompt. Only the benchmark table above uses independent
  human labels.
- **Bigger did not help.** ModernBERT-large, domain-adapted the same way,
  scored 0.6557 in an fp16 preview, statistically level with the base
  model. An fp32 rerun is outstanding.

## Engineering notes

Three findings that cost real time and are recorded so they cost nobody
else any:

- **MPS inference is not deterministic.** Identical input and weights
  disagreed on up to 79 of 595 sentences between repeats, swinging results
  by ~2 F1. CPU repeats were exact. Everything that reports a number now
  runs on CPU.
- **fp32 ModernBERT hits a pathological kernel path on MPS**, about 50
  s/step against 2.9 s/step in bfloat16, a 17x penalty that does not
  appear at short sequence lengths. Pretraining runs in bf16.
- **bf16 is fine for pretraining and wrong for fine-tuning.** With only
  ~2,000 supervised examples it cost 0.09 weighted F1 against fp32, and on
  a vanilla backbone it diverged outright (0.5622 then 0.0860).

## Reproducibility

One command per reported number, each appending to RESULTS.md with the
command, git commit, and date:

```bash
make ingest             # core corpus
make ingest-expanded    # speeches, testimony, archives
make bootstrap          # dictionary + LLM first-pass labels
make review             # human review queue (review-html for the browser)
make pretrain           # domain-adaptive pretraining
make train-benchmark    # fine-tune on the public benchmark
make gpt5-benchmark     # zero-shot LLM baseline
make eval-provisional   # three-way table on the held-out year
make probe              # negation minimal-pair probe
make yield-study        # 2-year Treasury correlation
make event-study        # FX decisions and the chart
make cost               # inference cost and speed
make test               # unit tests
```

The LLM labels behind every reported row are committed in
[data/llm_labels.csv](data/llm_labels.csv) and consulted before any API
call, so `make eval-provisional` and `make probe` reproduce their numbers
**offline with no API key**. Requires PostgreSQL (`DATABASE_URL`);
`OPENAI_API_KEY` only for fresh labelling. Pinned dependencies in
[requirements.lock](requirements.lock).

## Data sources

Federal Reserve and Bank of Canada websites; the FOMC hawkish-dovish
benchmark of Shah, Paturi & Chava (2023), CC BY-NC 4.0; USD/CAD from
Dukascopy tick history with the Bank of Canada Valet API as fallback;
2-year Treasury yields from FRED (DGS2). Labeling scheme and its sources
are in [labeling/codebook.md](labeling/codebook.md).

## Open threads

- No-DAPT control run, to measure whether domain adaptation improves the
  benchmark score or only the language-modelling loss
- ModernBERT-large fine-tune in fp32
- Human review of the held-out labels, which is what would turn the
  provisional evaluation into a headline one

## License

MIT for the code. The benchmark data is CC BY-NC 4.0; anything trained on
it inherits that restriction.
