"""Export every cached LLM label to one committed CSV.

The per-request cache under data/llm_cache/ is thousands of small files
and is not tracked. This consolidates it into a single auditable table so
that anyone can inspect the labels behind the reported numbers, and so
that `scripts/eval.py` can reproduce the LLM baseline row without an API
key: it primes the cache from this file before making any request.

Usage:
    python scripts/export_llm_labels.py
"""

import argparse
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CACHE_DIR = "data/llm_cache"
OUT_PATH = "data/llm_labels.csv"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default=CACHE_DIR)
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    if not os.path.isdir(args.cache_dir):
        raise SystemExit(f"{args.cache_dir} not found")

    rows = []
    for name in sorted(os.listdir(args.cache_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(args.cache_dir, name), encoding="utf-8") as f:
            blob = json.load(f)
        label = blob.get("label") or {}
        sentence = blob.get("sentence")
        if not sentence or "stance" not in label:
            continue
        usage = blob.get("usage") or {}
        rows.append({
            "model": blob.get("model", ""),
            "sentence_sha256": hashlib.sha256(sentence.encode()).hexdigest(),
            "stance": label["stance"],
            "topic": label.get("topic", ""),
            "prompt_tokens": usage.get("prompt_tokens", ""),
            "completion_tokens": usage.get("completion_tokens", ""),
            "sentence": sentence,
        })

    rows.sort(key=lambda r: (r["model"], r["sentence_sha256"]))
    fields = ["model", "sentence_sha256", "stance", "topic",
              "prompt_tokens", "completion_tokens", "sentence"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    by_model = {}
    for r in rows:
        by_model[r["model"]] = by_model.get(r["model"], 0) + 1
    print(f"wrote {len(rows)} labels to {args.out}")
    for model, n in sorted(by_model.items()):
        print(f"  {model}: {n}")


if __name__ == "__main__":
    main()
