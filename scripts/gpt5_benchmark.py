"""Zero-shot GPT-5 on the Trillion Dollar Words held-out test split.

The prompt states the benchmark's own label definitions, adapted from the
annotation guide in Shah, Paturi & Chava (2023), so the LLM competes on
the same understanding of the task a human annotator had. Responses are
cached; the run is billed once.

Usage:
    python scripts/gpt5_benchmark.py [--model gpt-5]
"""

import argparse
import csv
import os
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from sklearn.metrics import accuracy_score, classification_report, f1_score

from cbsent import llm_label

BENCH_DIR = "data/benchmark"
CACHE_DIR = "data/llm_cache"
ID2LABEL = {0: "dovish", 1: "hawkish", 2: "neutral"}

# Adapted from the benchmark's annotation guide: sentence-level monetary
# policy stance of FOMC communication.
BENCH_PROMPT = """\
You classify single sentences from FOMC communications (meeting minutes,
speeches, press conferences) by monetary policy stance. Answer with
exactly one of: hawkish, dovish, neutral.

- hawkish: the sentence indicates a tightening of monetary policy or an
  economic reading that supports tightening: rising or above-target
  inflation or inflation expectations, an overheating economy or labour
  market, rate increases, reduced accommodation or balance sheet runoff.
- dovish: the sentence indicates an easing of monetary policy or an
  economic reading that supports easing: falling or below-target
  inflation, economic weakness or slack, rate cuts, added accommodation
  or asset purchases.
- neutral: mixed or balanced readings, statements of fact with no
  directional implication for policy, or procedural/descriptive language.

Judge the sentence on its own. Respond with JSON: {"stance": "..."}"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-5")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    with open(os.path.join(BENCH_DIR, "test.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    texts = [r["sentence"] for r in rows]
    y_true = [ID2LABEL[int(r["label"])] for r in rows]
    print(f"benchmark test split: {len(rows)} sentences")

    labels = llm_label.label_many(
        texts, args.model, CACHE_DIR, workers=args.workers,
        system_prompt=BENCH_PROMPT, require_topic=False,
    )
    missing = sum(1 for l in labels if l is None)
    preds = [l["stance"] if l else "neutral" for l in labels]
    if missing:
        print(f"warning: {missing} responses invalid, scored neutral")

    weighted = f1_score(y_true, preds, average="weighted")
    macro = f1_score(y_true, preds, average="macro")
    acc = accuracy_score(y_true, preds)
    print(f"\n{args.model} zero-shot on TDW test: "
          f"weighted F1 {weighted:.4f}  macro F1 {macro:.4f}  acc {acc:.4f}")
    print(classification_report(y_true, preds, zero_division=0))

    if not args.no_results_append:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        entry = (
            f"\n## Zero-shot {args.model} on the TDW benchmark test split "
            f"({date.today().isoformat()})\n\n"
            f"- command: `python scripts/gpt5_benchmark.py --model {args.model}`\n"
            f"- git commit: `{commit}`\n"
            f"- prompt: benchmark label definitions, stance only, cached\n"
            f"- test sentences: {len(rows)}, invalid responses: {missing}\n\n"
            f"| metric | value |\n|---|---|\n"
            f"| weighted F1 (benchmark standard) | {weighted:.4f} |\n"
            f"| macro F1 | {macro:.4f} |\n"
            f"| accuracy | {acc:.4f} |\n"
        )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("appended to RESULTS.md")


if __name__ == "__main__":
    main()
