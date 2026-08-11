"""Score the hand-written negation probe and report per-system accuracy.

The probe in data/negation_probe.csv is a set of minimal pairs written
against the codebook's decision rules: each pair holds the policy
vocabulary fixed and flips only the negation or the hedge, so a system
that keys on vocabulary alone scores at chance on the negated half while
a system that reads scope does not. The labels are the codebook's, not
samples from the corpus, and the rule number behind each one is recorded
in the file.

This measures the engine's negation claim directly, rather than inferring
it from an aggregate that negated sentences barely influence.

Usage:
    python scripts/negation_probe.py [--model-dir export/cbsent]
"""

import argparse
import csv
import os
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

from cbsent import dictionary, llm_label
from cbsent.negation import mark_cues

PROBE_CSV = "data/negation_probe.csv"
CACHE_DIR = "data/llm_cache"
LLM_LABELS_CSV = "data/llm_labels.csv"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default="export/cbsent")
    parser.add_argument("--llm-model", default="gpt-5")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    with open(PROBE_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    texts = [r["text"] for r in rows]
    y_true = [r["stance"] for r in rows]
    # A "negated" item is one whose text carries a negation cue.
    negated = [i for i, t in enumerate(texts) if mark_cues(t) != t
               and any(c in t.lower() for c in (" not ", "no longer", " no "))]
    print(f"probe items: {len(rows)}, of which {len(negated)} carry a negation cue")

    systems = {"dictionary": [dictionary.classify(t) for t in texts]}

    if not args.skip_llm:
        primed = llm_label.prime_from_csv(LLM_LABELS_CSV)
        if primed:
            print(f"primed {primed} labels from {LLM_LABELS_CSV}")
        labels = llm_label.label_many(texts, args.llm_model, CACHE_DIR,
                                      workers=8, progress_every=0)
        systems[f"zero-shot {args.llm_model}"] = [
            l["stance"] if l else "neutral" for l in labels
        ]

    from cbsent.model import Scorer
    scorer = Scorer(args.model_dir, device=args.device)
    systems["cbsent (fine-tuned)"] = [
        r["stance"] for r in scorer.score_sentences(texts)
    ]

    def accuracy(preds, idx=None):
        idx = range(len(preds)) if idx is None else idx
        if not list(idx):
            return float("nan")
        hits = sum(1 for i in idx if preds[i] == y_true[i])
        return hits / len(list(idx))

    lines = [
        "| system | all items | negated items | non-negated items | "
        "distinct labels used on negated items |",
        "|---|---|---|---|---|",
    ]
    plain = [i for i in range(len(texts)) if i not in negated]
    degenerate = {}
    for name, preds in systems.items():
        # A system that answers with one label for every negated item is not
        # reading scope; its accuracy there is the label mix, nothing more.
        used = sorted({preds[i] for i in negated})
        degenerate[name] = used
        lines.append(
            f"| {name} | {accuracy(preds):.2f} ({sum(1 for i in range(len(preds)) if preds[i] == y_true[i])}"
            f"/{len(preds)}) | {accuracy(preds, negated):.2f} "
            f"({sum(1 for i in negated if preds[i] == y_true[i])}/{len(negated)}) | "
            f"{accuracy(preds, plain):.2f} "
            f"({sum(1 for i in plain if preds[i] == y_true[i])}/{len(plain)}) | "
            f"{len(used)} ({', '.join(used)}) |"
        )
    table = "\n".join(lines)
    print("\n" + table)
    for name, used in degenerate.items():
        if len(used) == 1:
            print(f"\n{name} answered '{used[0]}' for every negated item, so its "
                  f"score on that subset reflects the label mix, not negation "
                  f"sensitivity.")

    print("\nnegated items, per system:")
    header = f"{'expected':<9}" + "".join(f"{n[:18]:<20}" for n in systems)
    print(header)
    for i in negated:
        row = f"{y_true[i]:<9}" + "".join(f"{systems[n][i]:<20}" for n in systems)
        print(row)
        print(f"          {texts[i][:96]}")

    if not args.no_results_append:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        entry = (
            f"\n## Negation probe ({date.today().isoformat()})\n\n"
            f"- command: `python scripts/negation_probe.py`\n"
            f"- git commit: `{commit}`\n"
            f"- probe: {len(rows)} hand-written minimal pairs in "
            f"`{PROBE_CSV}`, labelled by the codebook rules cited per row, "
            f"{len(negated)} of them carrying a negation cue\n"
            f"- inference device: {args.device}\n\n"
            f"{table}\n"
        )
        for name, used in degenerate.items():
            if len(used) == 1:
                entry += (
                    f"\n{name} answered `{used[0]}` for every one of the "
                    f"{len(negated)} negated items. Its score on that subset is "
                    f"therefore the label mix of the subset and carries no "
                    f"evidence of negation sensitivity.\n"
                )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("\nappended to RESULTS.md")


if __name__ == "__main__":
    main()
