"""Evaluate the fine-tuned model against both baselines on the held-out year.

All three systems label the identical set of held-out sentences:
  A. dictionary method (Apel & Blix Grimaldi)
  B. zero-shot GPT-5, same instructions the human annotators got, cached
  C. the fine-tuned cbsent model

By default only human-verified sentences count; running with
--allow-bootstrap includes LLM-bootstrap labels and stamps the output
accordingly (numbers produced that way are provisional, not headline).

Appends the table to RESULTS.md with the command, git commit, and date.

Usage:
    python scripts/eval.py [--cut-date 2025-08-01] [--eval-end 2026-08-01]
                           [--model-dir export/cbsent] [--gpt5-model gpt-5]
                           [--allow-bootstrap] [--no-results-append]
"""

import argparse
import os
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from sklearn.metrics import classification_report, f1_score

from cbsent import dictionary, llm_label
from cbsent.ingest import db
from cbsent.model import Scorer

CACHE_DIR = "data/llm_cache"


def load_eval_rows(conn, cut_date: str, eval_end: str, allow_bootstrap: bool):
    """Held-out sentences with a resolved reference label.

    Human labels win where they exist. Restricting to sentences where the
    two bootstrap labellers agree was tried and rejected: it makes the
    reference identical to the dictionary's own output on every surviving
    row, so the dictionary cannot lose. See the correction in RESULTS.md.
    """
    source_expr = "coalesce(h.stance, l.stance)" if allow_bootstrap else "h.stance"
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT s.id, s.text, {source_expr} AS stance,
                   (h.sentence_id IS NOT NULL) AS is_human
            FROM sentences s
            LEFT JOIN labels h ON h.sentence_id = s.id AND h.source = 'human'
            LEFT JOIN labels l ON l.sentence_id = s.id AND l.source = 'llm'
            WHERE s.published_at >= %s AND s.published_at < %s
              AND {source_expr} IS NOT NULL
            ORDER BY s.id
            """,
            (cut_date, eval_end),
        )
        return cur.fetchall()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cut-date", default="2025-08-01")
    parser.add_argument("--eval-end", default="2026-08-01")
    parser.add_argument("--model-dir", default="export/cbsent")
    parser.add_argument("--gpt5-model", default="gpt-5")
    parser.add_argument("--allow-bootstrap", action="store_true")
    parser.add_argument("--skip-gpt5", action="store_true")
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--device", default="cpu",
                        help="inference device; cpu is the default because MPS "
                             "inference is not reproducible (see RESULTS.md)")
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    with db.connect() as conn:
        rows = load_eval_rows(conn, args.cut_date, args.eval_end,
                              args.allow_bootstrap)
    if not rows:
        raise SystemExit("no labelled sentences in the evaluation window")

    texts = [r[1] for r in rows]
    y_true = [r[2] for r in rows]
    n_human = sum(1 for r in rows if r[3])
    provenance = f"{n_human}/{len(rows)} human-verified"
    print(f"eval window {args.cut_date} to {args.eval_end}: "
          f"{len(rows)} sentences ({provenance})")

    systems = {}

    systems["dictionary"] = [dictionary.classify(t) for t in texts]

    if not args.skip_gpt5:
        print(f"labelling {len(texts)} sentences with {args.gpt5_model}...")
        labels = llm_label.label_many(texts, args.gpt5_model, CACHE_DIR,
                                      workers=args.workers)
        missing = sum(1 for l in labels if l is None)
        # An unusable response is scored as the majority class rather than
        # dropped, so all systems are compared on identical sentences.
        preds = [l["stance"] if l else "neutral" for l in labels]
        if missing:
            print(f"warning: {missing} {args.gpt5_model} responses invalid, scored neutral")
        systems[f"zero-shot {args.gpt5_model}"] = preds

    scorer = Scorer(args.model_dir, device=args.device)
    model_out = scorer.score_sentences(texts)
    systems["cbsent (fine-tuned)"] = [r["stance"] for r in model_out]

    lines = []
    lines.append(f"| system | macro-F1 | hawkish F1 | dovish F1 | neutral F1 |")
    lines.append(f"|---|---|---|---|---|")
    for name, preds in systems.items():
        macro = f1_score(y_true, preds, average="macro")
        per = f1_score(y_true, preds, average=None,
                       labels=["hawkish", "dovish", "neutral"])
        lines.append(f"| {name} | {macro:.4f} | {per[0]:.4f} | {per[1]:.4f} | {per[2]:.4f} |")
    table = "\n".join(lines)
    print("\n" + table + "\n")

    for name, preds in systems.items():
        print(f"--- {name} ---")
        print(classification_report(y_true, preds, zero_division=0))

    if not args.no_results_append:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        bootstrap_share = len(rows) - n_human
        caveat = ""
        if bootstrap_share:
            caveat = (
                f"\nPROVISIONAL. {bootstrap_share} of {len(rows)} reference labels "
                f"come from the gpt-5-mini bootstrap pass rather than a human. "
                f"Two of the three systems are therefore partly measured against "
                f"themselves: the zero-shot baseline shares a model family and "
                f"prompt with the labeller, and the fine-tuned model was trained "
                f"on those labels. Read the zero-shot row as an upper bound "
                f"inflated by that overlap, not as accuracy. The headline "
                f"comparison is the margin over the dictionary baseline, which "
                f"shares nothing with the labeller. This table becomes a headline "
                f"result only when the held-out labels are human-verified.\n"
            )
        title = "Stance macro-F1"
        entry = (
            f"\n## {title}, held-out {args.cut_date} to {args.eval_end}"
            f" ({date.today().isoformat()})\n\n"
            f"- command: `python scripts/eval.py --cut-date {args.cut_date}"
            f" --eval-end {args.eval_end}"
            f"{' --allow-bootstrap' if args.allow_bootstrap else ''}"
            f"{' --skip-gpt5' if args.skip_gpt5 else ''}`\n"
            f"- git commit: `{commit}`\n"
            f"- eval sentences: {len(rows)} ({provenance})\n"
            f"- inference device: {args.device}\n"
            f"- label provenance: "
            f"{'human-verified only' if not bootstrap_share else 'includes bootstrap labels'}\n\n"
            f"{table}\n"
            f"{caveat}"
        )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("appended to RESULTS.md")


if __name__ == "__main__":
    main()
