# labeling/

## Files

- `codebook.md` — the label definitions, the literature they adapt, and
  worked negation and hedge cases. Read this before reviewing.
- `review.py` — terminal reviewer, writes to the database directly.
- `review_html.py` — generates a single-page browser reviewer, exports a
  CSV that `scripts/import_review.py` loads back.

## Why review is the gate

Bootstrap labels come from the dictionary method and an LLM pass. Neither
is ground truth, and an evaluation against LLM labels cannot be a
headline result: the zero-shot LLM baseline shares a model family and a
prompt with the labeller, and the fine-tuned model was trained on those
same labels, so both are measured partly against themselves.

Human labels break that circle. Priority order is therefore:

1. **The held-out window** (every labelled sentence published on or after
   the cut date). This is the evaluation set; the three-way table is only
   defensible once these are human-verified.
2. **Dictionary/LLM disagreements** in the training window, where the two
   bootstrap labellers contradict each other and one of them is wrong.
3. **A stratified sample of agreements**, to catch cases where both
   labellers are wrong in the same direction.

## Negated sentences deserve extra attention

The negation probe (`make probe`) shows the trained model answering
hawkish for every negated item in it, while a zero-shot frontier LLM gets
all of them right. The likely cause is coverage: negated policy
constructions are rare in ordinary corpus sentences, so they carry almost
no weight in either the training signal or the aggregate metric.

When reviewing, treat any sentence containing "not", "no longer", "does
not", or "unlikely" as high value even if it looks easy, and prefer
correcting those over confirming a straightforward one. The queue does not
currently over-sample them; doing so by hand is the cheapest available
fix.

## Reviewing in the browser

```bash
make review-html
open labeling/review.html
```

Click a stance for each sentence and adjust the topic dropdown if the
suggested topic is wrong. Progress is saved in the browser, so the page
can be closed and reopened. When done, click "Download decisions CSV" and
load it:

```bash
python scripts/import_review.py ~/Downloads/reviewed.csv
```

## Reviewing in the terminal

```bash
make review
```

Keys are `h`, `d`, `n` for stance, then `1`-`5` for topic (enter keeps the
suggested topic), `s` to skip, `q` to quit. Each decision is committed
immediately, so quitting loses nothing.

## After reviewing

```bash
make train && make eval
```

`train` prefers human labels wherever they exist and falls back to
bootstrap labels elsewhere; `eval` uses human labels only unless
`--allow-bootstrap` is passed. The count of human labels used is recorded
in the exported training config and in RESULTS.md.
