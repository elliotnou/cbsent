"""Publish the fine-tuned weights and model card to the Hugging Face Hub.

The card is generated from the committed artefacts: the training config
written by scripts/train.py and the evaluation table in RESULTS.md, so it
cannot claim a number that was not produced by a script.

Nothing is uploaded without --push, and --push requires the repo id to be
given explicitly.

Usage:
    python scripts/publish_hub.py --repo-id <user>/<name>            # dry run
    python scripts/publish_hub.py --repo-id <user>/<name> --push
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

CARD_TEMPLATE = """---
license: mit
language: en
library_name: transformers
tags:
  - text-classification
  - finance
  - monetary-policy
base_model: distilbert-base-uncased
---

# {repo_id}

Multi-task DistilBERT for hawkish-dovish stance and topic in Federal
Reserve and Bank of Canada communications. Trained and evaluated with
[cbsent]({source_url}).

## Task

Two heads over a shared `[CLS]` representation:

- stance: {stance_labels}
- topic: {topic_labels}

Negation and hedge cues are marked inline before encoding
({negation_note}), so negated policy language such as "not yet
appropriate to raise the target range" is not read as hawkish.

## Training data

Sentences from FOMC statements, FOMC minutes and Bank of Canada rate
announcements, segmented with rules tuned to central bank prose. Labels
follow the codebook in the repository, which adapts the annotation
schemes of Shah, Paturi & Chava (2023) and Apel & Blix Grimaldi (2012).

- training sentences: {train_sentences}
- validation sentences (chronological, from {val_start}): {val_sentences}
- human-verified labels in the training window: {human_labelled}
- training cut date: {cut_date} (nothing published on or after this date
  was seen during training or model selection)

{label_provenance}

## Evaluation

Chronological holdout only; no random splits. All systems scored on the
identical held-out sentences, on CPU.

{eval_table}

{eval_caveat}

## Intended use

Research on central bank communication: scoring sentences or documents
for policy stance, and building point-in-time tone indices where the
publication timestamp of every input is known.

## Limitations

- English only, and specific to Fed and BoC prose. Other central banks
  and other financial text are out of distribution.
- Labels are sentence-level and context-free by construction: a sentence
  whose stance depends on the surrounding paragraph is labelled neutral,
  so document-level nuance is lost.
- Part of the label set originates from an LLM bootstrap pass; the
  human-verified share is stated above.
- The stance score is a model output, not a forecast. Nothing here is
  investment advice.
- Class balance in central bank text is uneven; check the per-class
  numbers in the table above rather than relying on the macro average
  alone.
- Inference on Apple MPS is not reproducible: identical input scored
  twice on MPS disagreed on up to 79 of 595 sentences, while CPU
  inference was exact across repeats. Score on CPU when a number has to
  be reproducible.

## Reproducing

```bash
git clone {source_url}
cd cbsent && pip install -e .
make train && make eval
```

Training config: seed {seed}, {epochs} epochs, batch size {batch_size},
learning rate {lr}, max sequence length {max_seq_len}, backbone
`{backbone}`, trained on {device}. Git commit `{git_commit}`.
"""


def latest_eval_table(results_path: str) -> str:
    if not os.path.exists(results_path):
        return "_No evaluation recorded yet._"
    text = open(results_path, encoding="utf-8").read()
    tables = re.findall(r"(\| system \|.*?)(?=\n\n|\n#|\Z)", text, re.S)
    if not tables:
        return "_No evaluation recorded yet._"
    return tables[-1].strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", required=True,
                        help="target Hugging Face repo, e.g. user/cbsent-distilbert")
    parser.add_argument("--model-dir", default="export/cbsent")
    parser.add_argument("--results", default="RESULTS.md")
    parser.add_argument("--source-url", default="https://github.com/elliotnou/cbsent")
    parser.add_argument("--push", action="store_true",
                        help="actually upload; without this the card is only written")
    parser.add_argument("--publish-provisional", action="store_true",
                        help="allow publishing before any human label review")
    args = parser.parse_args()

    load_dotenv()

    config_path = os.path.join(args.model_dir, "config.json")
    if not os.path.exists(config_path):
        raise SystemExit(f"{config_path} not found; train a model first")
    config = json.load(open(config_path, encoding="utf-8"))

    human = config["human_labelled"]
    if human:
        label_provenance = (
            f"Labels were bootstrapped with the dictionary method and an LLM "
            f"pass, then reviewed by a human against the codebook; "
            f"{human} of the training labels are human-verified."
        )
        eval_caveat = ""
    else:
        label_provenance = (
            "Labels in this release come from the dictionary and LLM bootstrap "
            "passes only. No human review has been applied yet."
        )
        eval_caveat = (
            "**These numbers are provisional.** The reference labels for the "
            "held-out year come from an LLM bootstrap pass rather than a human, "
            "so the zero-shot row is inflated by sharing a model family and "
            "prompt with the labeller, and the fine-tuned row is measured "
            "partly against its own training signal. The defensible comparison "
            "in this release is the margin over the dictionary baseline, which "
            "shares nothing with the labeller. Treat the table as a pipeline "
            "check, not as accuracy."
        )

    card = CARD_TEMPLATE.format(
        repo_id=args.repo_id,
        source_url=args.source_url,
        label_provenance=label_provenance,
        eval_caveat=eval_caveat,
        stance_labels=", ".join(config["stance_labels"]),
        topic_labels=", ".join(config["topic_labels"]),
        negation_note=("enabled for these weights" if config["use_negation_markers"]
                       else "disabled for these weights"),
        train_sentences=config["train_sentences"],
        val_sentences=config["val_sentences"],
        val_start=config["val_start"],
        human_labelled=config["human_labelled"],
        cut_date=config["cut_date"],
        eval_table=latest_eval_table(args.results),
        seed=config["seed"], epochs=config["epochs"],
        batch_size=config["batch_size"], lr=config["lr"],
        max_seq_len=config["max_seq_len"], backbone=config["backbone"],
        device=config["device"], git_commit=config["git_commit"],
    )

    card_path = os.path.join(args.model_dir, "README.md")
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(card)
    print(f"model card written to {card_path}")

    if not args.push:
        print("dry run: nothing uploaded. Re-run with --push to publish.")
        return

    if not human and not args.publish_provisional:
        raise SystemExit(
            "refusing to publish: this model's labels have had no human review, "
            "so its evaluation table is provisional. Work through the review "
            "queue first, or pass --publish-provisional to publish anyway with "
            "the caveat shown on the card."
        )

    token = os.getenv("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN not set; cannot push")

    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.create_repo(repo_id=args.repo_id, exist_ok=True)
    api.upload_folder(repo_id=args.repo_id, folder_path=args.model_dir,
                      commit_message="publish cbsent weights and model card")
    print(f"pushed {args.model_dir} to https://huggingface.co/{args.repo_id}")


if __name__ == "__main__":
    main()
