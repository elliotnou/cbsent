"""Negation/hedge ablation across seeds.

One training run per variant cannot separate the effect of the input
transform from run-to-run variance, and on this corpus the two are the
same order of magnitude. This trains both variants at several seeds and
reports the mean and spread of held-out macro-F1, so the claim about
negation handling is stated as an effect size with a spread rather than a
single number.

Usage:
    python scripts/ablation_sweep.py --seeds 20250811 7 1234 [--epochs 6]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from statistics import mean, stdev

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sklearn.metrics import f1_score

from cbsent.ingest import db
from cbsent.model import Scorer
from cbsent.negation import mark_cues

WORK_DIR = "export/sweep"


def load_eval(cut_date: str, eval_end: str, allow_bootstrap: bool):
    source_expr = "coalesce(h.stance, l.stance)" if allow_bootstrap else "h.stance"
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT s.text, {source_expr} AS stance
            FROM sentences s
            LEFT JOIN labels h ON h.sentence_id = s.id AND h.source = 'human'
            LEFT JOIN labels l ON l.sentence_id = s.id AND l.source = 'llm'
            WHERE s.published_at >= %s AND s.published_at < %s
              AND {source_expr} IS NOT NULL
            ORDER BY s.id
            """,
            (cut_date, eval_end),
        )
        rows = cur.fetchall()
    return [r[0] for r in rows], [r[1] for r in rows]


def train_one(seed: int, markers: bool, cut_date: str, epochs: int) -> str:
    out_dir = os.path.join(WORK_DIR, f"{'neg' if markers else 'plain'}-{seed}")
    if os.path.exists(os.path.join(out_dir, "model.pt")):
        print(f"  reusing {out_dir}")
        return out_dir
    cmd = [
        sys.executable, "scripts/train.py", "--cut-date", cut_date,
        "--epochs", str(epochs), "--seed", str(seed), "--export-dir", out_dir,
    ]
    if not markers:
        cmd.append("--no-negation-markers")
    print(f"  training {out_dir}")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    return out_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[20250811, 7, 1234])
    parser.add_argument("--cut-date", default="2025-08-01")
    parser.add_argument("--eval-end", default="2026-08-01")
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--allow-bootstrap", action="store_true")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--keep-weights", action="store_true")
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    texts, y_true = load_eval(args.cut_date, args.eval_end, args.allow_bootstrap)
    if not texts:
        raise SystemExit("no labelled sentences in the evaluation window")
    cue_idx = [i for i, t in enumerate(texts) if mark_cues(t) != t]
    print(f"eval sentences: {len(texts)} ({len(cue_idx)} contain a cue)")

    results = {True: [], False: []}
    cue_results = {True: [], False: []}
    for markers in (True, False):
        for seed in args.seeds:
            out_dir = train_one(seed, markers, args.cut_date, args.epochs)
            preds = [r["stance"] for r in
                     Scorer(out_dir, device=args.device).score_sentences(texts)]
            macro = f1_score(y_true, preds, average="macro")
            macro_cue = f1_score([y_true[i] for i in cue_idx],
                                 [preds[i] for i in cue_idx], average="macro")
            results[markers].append(macro)
            cue_results[markers].append(macro_cue)
            print(f"  seed {seed} markers={markers}: "
                  f"macro-F1 {macro:.4f}, cue subset {macro_cue:.4f}")

    def summarize(values):
        spread = stdev(values) if len(values) > 1 else 0.0
        return mean(values), spread

    with_mean, with_sd = summarize(results[True])
    without_mean, without_sd = summarize(results[False])
    cue_with_mean, cue_with_sd = summarize(cue_results[True])
    cue_without_mean, cue_without_sd = summarize(cue_results[False])

    table = "\n".join([
        f"| variant | macro-F1 mean over {len(args.seeds)} seeds | sd | "
        f"cue-sentence macro-F1 mean | sd |",
        "|---|---|---|---|---|",
        f"| with negation markers | {with_mean:.4f} | {with_sd:.4f} | "
        f"{cue_with_mean:.4f} | {cue_with_sd:.4f} |",
        f"| without negation markers | {without_mean:.4f} | {without_sd:.4f} | "
        f"{cue_without_mean:.4f} | {cue_without_sd:.4f} |",
    ])
    delta = with_mean - without_mean
    delta_cue = cue_with_mean - cue_without_mean
    pooled = max(with_sd, without_sd)
    verdict = (
        "larger than the between-seed spread, so the transform has an effect "
        "on this corpus"
        if abs(delta) > pooled else
        "smaller than the between-seed spread, so this corpus cannot "
        "distinguish the transform's effect from training noise"
    )

    print("\n" + table)
    print(f"\neffect of cue marking: {delta:+.4f} macro-F1 overall "
          f"({delta_cue:+.4f} on cue sentences); {verdict}")

    if not args.no_results_append:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        entry = (
            f"\n## Negation/hedge ablation across seeds, held-out "
            f"{args.cut_date} to {args.eval_end} ({date.today().isoformat()})\n\n"
            f"- command: `python scripts/ablation_sweep.py --seeds "
            f"{' '.join(str(s) for s in args.seeds)} --epochs {args.epochs}"
            f"{' --allow-bootstrap' if args.allow_bootstrap else ''}`\n"
            f"- git commit: `{commit}`\n"
            f"- eval sentences: {len(texts)}, of which {len(cue_idx)} contain a cue\n"
            f"- inference device: {args.device}, training device: mps\n\n"
            f"{table}\n\n"
            f"Effect of cue marking: {delta:+.4f} macro-F1 overall and "
            f"{delta_cue:+.4f} on cue sentences. The effect is {verdict}.\n"
        )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("appended to RESULTS.md")

    if not args.keep_weights:
        shutil.rmtree(WORK_DIR, ignore_errors=True)
        print(f"removed {WORK_DIR}")


if __name__ == "__main__":
    main()
