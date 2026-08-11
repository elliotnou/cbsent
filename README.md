# cbsent

A hawkish-dovish sentiment engine for Federal Reserve and Bank of Canada
communications. Sentence-level stance and topic from a fine-tuned
DistilBERT, evaluated against the dictionary method from the literature
and zero-shot GPT-5 on a chronologically held-out year, and validated
with a point-in-time event study against USD/CAD.

This is a library, not a hosted app: an importable package, a CLI, and
scripts that reproduce every number reported in
[RESULTS.md](RESULTS.md).

## Install

```bash
pip install -e .
```

## Use

```python
from cbsent import score

result = score("Inflation remains elevated, and it is not yet appropriate to lower the target range.")
print(result["score"], result["stance"])
```

From the shell:

```bash
cbsent score statement.txt
cbsent segment statement.txt
```

## What it does

```
official sites          release timestamps        stance + topic          index
-------------           -----------------         --------------          -----
FOMC statements    -->  documents table      -->  DistilBERT        -->   Fed level
FOMC minutes            (published_at)            two heads:              minus
BoC announcements  -->  sentences table      -->  stance 3-class    -->   BoC level
                        (published_at)            topic 5-class           = divergence
```

Every document is stamped with its exact release time (FOMC 2:00 p.m. ET;
BoC 10:00 a.m. ET before 2024-01-24, 9:45 a.m. ET after), and every
sentence row carries that timestamp. The divergence index at any instant
reads only sentences whose `published_at` precedes it, so look-ahead is a
schema violation rather than a code review question.

Sentence segmentation is tuned to central bank prose: decimal rates,
dotted abbreviations, enumerated clauses in minutes, and long
semicolon-chained sentences that each carry their own stance.

Negation and hedge cues are marked inline before encoding, so
"it is not yet appropriate to raise rates" is not read as hawkish. The
effect of that transform is measured, not asserted; the ablation is in
RESULTS.md.

## Evaluation

Chronological split only. Training uses text published before the cut
date; the following year is never seen during training or model
selection. All three systems are scored on the identical held-out
sentences.

The eval table, the ablation, and the event study counts live in
[RESULTS.md](RESULTS.md), each with the command, git commit, and date
that produced it.

## Labeling

[labeling/codebook.md](labeling/codebook.md) defines the stance and topic
schemes, cites the literature they adapt, and gives worked
negation/hedge cases. Labels are bootstrapped with the dictionary method
plus an LLM pass, then human-reviewed through
[labeling/review.py](labeling/review.py); the review queue prioritizes
the held-out window and every bootstrap disagreement.

## Reproducibility

```bash
make ingest        # scrape and load documents and sentences
make bootstrap     # dictionary + LLM first-pass labels
make review        # human review queue
make train         # fine-tune, chronological split
make ablate        # negation/hedge ablation
make eval          # the three-way macro-F1 table
make event-study   # decisions, FX alignment, and the chart
make test          # unit tests
```

Requires PostgreSQL (`DATABASE_URL`) and, for the LLM passes,
`OPENAI_API_KEY`. Pinned dependencies are in
[requirements.lock](requirements.lock). Data sources: the Federal
Reserve and Bank of Canada websites; USD/CAD from Dukascopy tick history
with the Bank of Canada Valet daily rate as fallback.

## License

MIT
