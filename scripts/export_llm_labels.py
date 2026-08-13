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

    from cbsent.llm_label import SYSTEM_PROMPT, TDW_BENCH_PROMPT, _cache_key

    known_prompts = {"codebook": SYSTEM_PROMPT, "tdw_bench": TDW_BENCH_PROMPT}

    rows, unknown = [], 0
    for name in sorted(os.listdir(args.cache_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(args.cache_dir, name), encoding="utf-8") as f:
            blob = json.load(f)
        label = blob.get("label") or {}
        sentence = blob.get("sentence")
        model = blob.get("model", "")
        if not sentence or "stance" not in label:
            continue
        # The filename is the (model, prompt, sentence) hash, so the prompt
        # behind each cached response is verifiable even though the file
        # does not store the prompt text.
        prompt_name = None
        for candidate, text in known_prompts.items():
            if name[:-5] == _cache_key(model, sentence, text):
                prompt_name = candidate
                break
        if prompt_name is None:
            unknown += 1
            continue
        usage = blob.get("usage") or {}
        rows.append({
            "model": model,
            "prompt": prompt_name,
            "sentence_sha256": hashlib.sha256(sentence.encode()).hexdigest(),
            "stance": label["stance"],
            "topic": label.get("topic") or "",
            "prompt_tokens": usage.get("prompt_tokens", ""),
            "completion_tokens": usage.get("completion_tokens", ""),
            "sentence": sentence,
        })
    if unknown:
        print(f"note: {unknown} cache files did not match a known prompt and were skipped")

    rows.sort(key=lambda r: (r["model"], r["prompt"], r["sentence_sha256"]))
    fields = ["model", "prompt", "sentence_sha256", "stance", "topic",
              "prompt_tokens", "completion_tokens", "sentence"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    by_key = {}
    for r in rows:
        k = (r["model"], r["prompt"])
        by_key[k] = by_key.get(k, 0) + 1
    print(f"wrote {len(rows)} labels to {args.out}")
    for (model, prompt), n in sorted(by_key.items()):
        print(f"  {model} [{prompt}]: {n}")


if __name__ == "__main__":
    main()
