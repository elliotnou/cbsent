"""Seed sweep for the TDW benchmark fine-tune.

Trains the benchmark model at several seeds, with and without the BoC
extension, and reports mean and spread on the held-out test split. This
keeps single-run luck out of the headline comparison against the
zero-shot LLM, and measures whether the extension helps, hurts, or does
nothing - the multi-seed negation ablation earlier in RESULTS.md showed
how misleading one run per variant can be.

Usage:
    python scripts/benchmark_sweep.py [--seeds 20250811 7 1234]
                                      [--backbone export/modernbert-cb-dapt]
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def run_one(backbone: str, boc: int, seed: int, epochs: int) -> dict:
    out_dir = f"export/bench-sweep/boc{boc}-{seed}"
    cmd = [
        ".venv/bin/python", "scripts/train_benchmark.py",
        "--backbone", backbone,
        "--boc-sentences", str(boc),
        "--seed", str(seed),
        "--epochs", str(epochs),
        "--out", out_dir,
        "--no-results-append",
    ]
    print(f"  training boc={boc} seed={seed}")
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    with open(os.path.join(out_dir, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backbone", default="export/modernbert-cb-dapt")
    parser.add_argument("--seeds", type=int, nargs="+",
                        default=[20250811, 7, 1234])
    parser.add_argument("--boc-sentences", type=int, default=1200)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    variants = {f"with {args.boc_sentences} BoC sentences": args.boc_sentences,
                "without BoC extension": 0}
    results = {}
    for name, boc in variants.items():
        runs = [run_one(args.backbone, boc, seed, args.epochs)
                for seed in args.seeds]
        weighted = [r["test_weighted_f1"] for r in runs]
        macro = [r["test_macro_f1"] for r in runs]
        results[name] = {
            "weighted": weighted, "macro": macro,
            "best_val_seed": max(runs, key=lambda r: r["best_val_weighted_f1"])["seed"],
        }
        print(f"{name}: weighted F1 per seed {weighted}")

    lines = [
        "| variant | weighted F1 mean | sd | min | max | macro F1 mean |",
        "|---|---|---|---|---|---|",
    ]
    for name, r in results.items():
        w = r["weighted"]
        lines.append(
            f"| {name} | {statistics.mean(w):.4f} | "
            f"{statistics.stdev(w) if len(w) > 1 else 0:.4f} | {min(w):.4f} | "
            f"{max(w):.4f} | {statistics.mean(r['macro']):.4f} |"
        )
    table = "\n".join(lines)
    print("\n" + table)

    if not args.no_results_append:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        entry = (
            f"\n## TDW benchmark fine-tune across seeds "
            f"({date.today().isoformat()})\n\n"
            f"- command: `python scripts/benchmark_sweep.py --backbone {args.backbone}"
            f" --seeds {' '.join(str(s) for s in args.seeds)}"
            f" --boc-sentences {args.boc_sentences} --epochs {args.epochs}`\n"
            f"- git commit: `{commit}`\n"
            f"- test split evaluated once per trained run, on cpu\n\n"
            f"{table}\n"
        )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("appended to RESULTS.md")


if __name__ == "__main__":
    main()
