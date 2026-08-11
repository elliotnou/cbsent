"""Measure the effect of negation/hedge cue marking.

Scores both trained variants on the identical held-out sentences and
reports the macro-F1 difference, plus the difference restricted to
sentences that actually contain a negation or hedge cue, which is where
the transform can matter at all.

Both variants must already be trained:
    make ablate

Usage:
    python scripts/ablation.py [--cut-date 2025-08-01] [--eval-end 2026-08-01]
"""

import argparse
import os
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sklearn.metrics import f1_score

from cbsent.ingest import db
from cbsent.model import Scorer
from cbsent.negation import mark_cues

VARIANTS = {
    "with negation markers": "export/cbsent",
    "without negation markers": "export/cbsent-no-negation",
}


def has_cue(text: str) -> bool:
    return mark_cues(text) != text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cut-date", default="2025-08-01")
    parser.add_argument("--eval-end", default="2026-08-01")
    parser.add_argument("--allow-bootstrap", action="store_true")
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    source_expr = "coalesce(h.stance, l.stance)" if args.allow_bootstrap else "h.stance"
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
            (args.cut_date, args.eval_end),
        )
        rows = cur.fetchall()

    if not rows:
        raise SystemExit("no labelled sentences in the evaluation window")

    texts = [r[0] for r in rows]
    y_true = [r[1] for r in rows]
    cue_idx = [i for i, t in enumerate(texts) if has_cue(t)]
    print(f"eval sentences: {len(rows)} ({len(cue_idx)} contain a negation or hedge cue)")

    lines = ["| variant | macro-F1 (all) | macro-F1 (cue sentences) |", "|---|---|---|"]
    scores = {}
    for name, model_dir in VARIANTS.items():
        if not os.path.exists(os.path.join(model_dir, "model.pt")):
            raise SystemExit(f"{model_dir} has no trained model; run make ablate")
        preds = [r["stance"] for r in Scorer(model_dir).score_sentences(texts)]
        macro_all = f1_score(y_true, preds, average="macro")
        macro_cue = (
            f1_score([y_true[i] for i in cue_idx], [preds[i] for i in cue_idx],
                     average="macro")
            if cue_idx else float("nan")
        )
        scores[name] = (macro_all, macro_cue)
        lines.append(f"| {name} | {macro_all:.4f} | {macro_cue:.4f} |")

    with_m = scores["with negation markers"]
    without_m = scores["without negation markers"]
    delta_all = with_m[0] - without_m[0]
    delta_cue = with_m[1] - without_m[1]
    table = "\n".join(lines)
    print("\n" + table)
    print(f"\neffect of cue marking: {delta_all:+.4f} macro-F1 overall, "
          f"{delta_cue:+.4f} on cue sentences")

    if not args.no_results_append:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        entry = (
            f"\n## Negation/hedge ablation, held-out {args.cut_date} to "
            f"{args.eval_end} ({date.today().isoformat()})\n\n"
            f"- command: `python scripts/ablation.py --cut-date {args.cut_date}"
            f" --eval-end {args.eval_end}"
            f"{' --allow-bootstrap' if args.allow_bootstrap else ''}`\n"
            f"- git commit: `{commit}`\n"
            f"- eval sentences: {len(rows)}, of which {len(cue_idx)} contain a cue\n\n"
            f"{table}\n\n"
            f"Effect of cue marking: {delta_all:+.4f} macro-F1 overall, "
            f"{delta_cue:+.4f} on cue sentences.\n"
        )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("appended to RESULTS.md")


if __name__ == "__main__":
    main()
