"""Compare inference cost and speed: local fine-tuned model vs the LLM baseline.

Local throughput is measured on this machine. LLM cost is computed from
real usage returned by the API, including reasoning tokens, which are
billed but never appear in the response text. Prices are arguments, not
constants, and the value used is recorded in RESULTS.md alongside its
source.

Usage:
    python scripts/cost_compare.py --sample 40 \
        --input-price 1.25 --output-price 10.00 \
        --price-source https://developers.openai.com/api/docs/pricing
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

from cbsent import llm_label
from cbsent.ingest import db
from cbsent.model import Scorer

CACHE_DIR = "data/llm_cache"


def local_throughput(model_dir: str, sentences, device: str,
                     repeats: int = 3) -> tuple:
    scorer = Scorer(model_dir, device=device)
    scorer.score_sentences(sentences[:8])  # warm the graph
    best = None
    for _ in range(repeats):
        start = time.perf_counter()
        scorer.score_sentences(sentences)
        elapsed = time.perf_counter() - start
        best = elapsed if best is None else min(best, elapsed)
    return len(sentences) / best, str(scorer.device)


def llm_usage(sentences, model: str, workers: int) -> tuple:
    """Label sentences and return mean prompt and completion tokens."""
    start = time.perf_counter()
    llm_label.label_many(sentences, model, CACHE_DIR, workers=workers,
                         progress_every=0)
    elapsed = time.perf_counter() - start

    prompt_tokens, completion_tokens, counted = 0, 0, 0
    for sentence in sentences:
        path = os.path.join(CACHE_DIR, llm_label._cache_key(model, sentence) + ".json")
        if not os.path.exists(path):
            continue
        usage = json.load(open(path, encoding="utf-8")).get("usage") or {}
        if "prompt_tokens" in usage:
            prompt_tokens += usage["prompt_tokens"]
            completion_tokens += usage["completion_tokens"]
            counted += 1
    if not counted:
        raise SystemExit("no usage recorded; the cache predates usage capture")
    return prompt_tokens / counted, completion_tokens / counted, elapsed, counted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default="export/cbsent")
    parser.add_argument("--llm-model", default="gpt-5")
    parser.add_argument("--sample", type=int, default=40,
                        help="uncached sentences to send to the API for usage measurement")
    parser.add_argument("--local-sentences", type=int, default=512)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--device", default=None,
                        help="inference device for the throughput measurement; "
                             "defaults to the fastest available")
    parser.add_argument("--input-price", type=float, required=True,
                        help="USD per million input tokens")
    parser.add_argument("--output-price", type=float, required=True,
                        help="USD per million output tokens")
    parser.add_argument("--price-source", required=True)
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    # Local throughput is measured on held-out text; the usage sample uses
    # training-window sentences so it is guaranteed not to be cached for
    # this model and therefore measures a real API call.
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT text FROM sentences WHERE published_at >= '2025-08-01'
            ORDER BY id LIMIT %s
            """,
            (args.local_sentences,),
        )
        local_sentences = [r[0] for r in cur.fetchall()]
        cur.execute(
            """
            SELECT text FROM sentences WHERE published_at < '2025-08-01'
            ORDER BY id DESC LIMIT %s
            """,
            (args.sample,),
        )
        sample = [r[0] for r in cur.fetchall()]

    rate, device = local_throughput(args.model_dir, local_sentences, args.device)
    print(f"local: {rate:.1f} sentences/second on {device} "
          f"({len(local_sentences)} sentences)")

    mean_in, mean_out, elapsed, counted = llm_usage(sample, args.llm_model, args.workers)
    per_sentence_usd = (mean_in * args.input_price + mean_out * args.output_price) / 1e6
    per_1k_usd = per_sentence_usd * 1000
    api_rate = counted / elapsed if elapsed else float("nan")
    print(f"{args.llm_model}: {mean_in:.0f} prompt + {mean_out:.0f} completion "
          f"tokens per sentence over {counted} sentences")
    print(f"{args.llm_model}: {api_rate:.1f} sentences/second at {args.workers} workers")
    print(f"{args.llm_model}: ${per_sentence_usd:.6f} per sentence, "
          f"${per_1k_usd:.2f} per 1,000 sentences")
    print(f"local: $0.00 marginal per sentence (runs on {device})")

    table = "\n".join([
        "| system | throughput | tokens per sentence | marginal cost per 1,000 sentences |",
        "|---|---|---|---|",
        f"| cbsent (fine-tuned, local) | {rate:.1f} sentences/s on {device} | n/a | $0.00 |",
        f"| zero-shot {args.llm_model} | {api_rate:.1f} sentences/s at "
        f"{args.workers} workers | {mean_in:.0f} in + {mean_out:.0f} out | ${per_1k_usd:.2f} |",
    ])

    if not args.no_results_append:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        entry = (
            f"\n## Inference cost and speed ({date.today().isoformat()})\n\n"
            f"- command: `python scripts/cost_compare.py --sample {args.sample}"
            f" --input-price {args.input_price} --output-price {args.output_price}"
            f" --price-source {args.price_source}`\n"
            f"- git commit: `{commit}`\n"
            f"- prices used: ${args.input_price} per million input tokens, "
            f"${args.output_price} per million output tokens, from "
            f"{args.price_source}\n"
            f"- token counts are real API usage over {counted} uncached sentences and "
            f"include reasoning tokens, which are billed but absent from the "
            f"response text\n\n"
            f"{table}\n"
        )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("appended to RESULTS.md")


if __name__ == "__main__":
    main()
