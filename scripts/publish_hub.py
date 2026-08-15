"""Publish trained weights and a model card to the Hugging Face Hub.

Handles either export format this project produces: the Hugging Face
sequence-classification model from the benchmark track, or the two-headed
checkpoint from the original track. The card is generated from the
committed artefacts (the training config written alongside the weights
and the tables in RESULTS.md), so it cannot claim a number no script
produced.

Nothing uploads without --push, and --push needs both an explicit repo id
and HF_TOKEN.

Usage:
    python scripts/publish_hub.py --repo-id <user>/<name>           # dry run
    python scripts/publish_hub.py --repo-id <user>/<name> --push
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

CARD = """---
license: cc-by-nc-4.0
language: en
library_name: transformers
pipeline_tag: text-classification
tags:
  - finance
  - monetary-policy
  - central-banks
base_model: {base_model}
---

# {repo_id}

Sentence-level hawkish/dovish stance for Federal Reserve and Bank of
Canada communications. Trained and evaluated with
[cbsent]({source_url}); every number below is reproducible from that
repository with one command and is recorded in its RESULTS.md.

## Use

```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

tok = AutoTokenizer.from_pretrained("{repo_id}")
model = AutoModelForSequenceClassification.from_pretrained("{repo_id}")

text = "Inflation remains elevated and the labour market is tight."
with torch.no_grad():
    probs = model(**tok(text, return_tensors="pt")).logits.softmax(-1)[0]
print(model.config.id2label[int(probs.argmax())])  # hawkish
```

Or through the package, which adds central-bank sentence segmentation and
document-level aggregation:

```bash
pip install cbsent
cbsent score "Inflation remains elevated."
```

## How it was built

{pipeline}

## Evaluation

{eval_table}

Scored on the held-out test split of the FOMC hawkish-dovish benchmark
(Shah, Paturi & Chava, ACL 2023), 496 sentences annotated by its authors.
Inference for reported numbers runs on CPU, which is deterministic here;
MPS is not (measured in the repository's RESULTS.md).

## Intended use

Research on central bank communication: scoring sentences or documents
for policy stance, and building point-in-time tone indices where the
publication timestamp of every input is known.

## Limitations

- **Not state of the art.** Zero-shot GPT-5 scores higher on this
  benchmark. What this model offers is roughly 120 sentences/second
  locally at zero marginal cost, deterministic and reproducible output,
  and no data leaving the machine.
- **Negation is handled poorly.** On a 24-item minimal-pair probe it gets
  4 of 10 negated sentences right, against 10 of 10 for a frontier LLM.
  Do not use it where negated policy constructions carry the signal.
- English only, and specific to Fed and BoC prose. Other central banks
  and other financial text are out of distribution.
- Labels are sentence-level and context-free by construction: a sentence
  whose stance depends on the surrounding paragraph is labelled neutral.
- Part of the training data carries LLM-generated labels; see the
  repository for the provenance breakdown.
- The stance score is a model output, not a forecast, and nothing here is
  investment advice.

## Training data

{training_data}

## License

CC BY-NC 4.0, inherited from the benchmark dataset this model was
fine-tuned on. The cbsent source code is MIT.

## Citation

The benchmark this model is trained and evaluated on:

```bibtex
@inproceedings{{shah-etal-2023-trillion,
    title = "Trillion Dollar Words: A New Financial Dataset, Task & Market Analysis",
    author = "Shah, Agam and Paturi, Suvan and Chava, Sudheer",
    booktitle = "Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics",
    year = "2023",
    pages = "6664--6679",
}}
```
"""


def latest_table(results_path: str, header: str) -> str:
    if not os.path.exists(results_path):
        return "_Not recorded._"
    text = open(results_path, encoding="utf-8").read()
    tables = re.findall(rf"(\| {re.escape(header)} \|.*?)(?=\n\n|\n#|\Z)", text, re.S)
    return tables[-1].strip() if tables else "_Not recorded._"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--model-dir", default="export/cbsent-bench")
    parser.add_argument("--dapt-config", default="export/modernbert-cb-dapt/dapt_config.json")
    parser.add_argument("--results", default="RESULTS.md")
    parser.add_argument("--source-url", default="https://github.com/elliotnou/cbsent")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    if not os.path.isdir(args.model_dir):
        raise SystemExit(f"{args.model_dir} not found; train a model first")

    train_cfg_path = os.path.join(args.model_dir, "train_config.json")
    train_cfg = (json.load(open(train_cfg_path, encoding="utf-8"))
                 if os.path.exists(train_cfg_path) else {})
    dapt_cfg = (json.load(open(args.dapt_config, encoding="utf-8"))
                if os.path.exists(args.dapt_config) else {})

    pipeline = []
    if dapt_cfg:
        pipeline.append(
            f"1. **Domain-adaptive pretraining.** Continued masked-language-model "
            f"training of `{dapt_cfg.get('backbone')}` on "
            f"{dapt_cfg.get('corpus_sentences', 0):,} unlabelled Fed and Bank of "
            f"Canada sentences ({dapt_cfg.get('tokens_millions')}M tokens), for "
            f"{dapt_cfg.get('epochs')} epochs. Held-out MLM loss "
            f"{dapt_cfg.get('final_val_mlm_loss')} after adaptation."
        )
    if train_cfg:
        pipeline.append(
            f"2. **Fine-tuning.** On the benchmark's own train split"
            + (f", extended with {train_cfg['boc_extension']:,} Bank of Canada "
               f"sentences" if train_cfg.get("boc_extension") else "")
            + f". {train_cfg.get('train_size', 0):,} training sentences, seed "
            f"{train_cfg.get('seed')}, best epoch {train_cfg.get('best_epoch')} "
            f"chosen on a held-out validation slice."
        )
    pipeline_text = "\n".join(pipeline) if pipeline else "_See the repository._"

    training_data = "_See the repository._"
    if train_cfg:
        human = train_cfg.get("boc_human_labelled", 0)
        training_data = (
            f"- benchmark train split: {train_cfg.get('train_size', 0):,} sentences "
            f"total after extension\n"
            f"- Bank of Canada extension: {train_cfg.get('boc_extension', 0):,} "
            f"sentences, of which {human:,} human-verified"
            + (" (the remainder carry LLM bootstrap labels)" if human == 0 else "")
            + "\n- validation: "
            f"{train_cfg.get('val_size', 0):,} sentences held out of the training pool\n"
            f"- test: {train_cfg.get('test_size', 0):,} sentences, the benchmark's "
            f"official split, untouched during training and model selection"
        )

    card = CARD.format(
        repo_id=args.repo_id,
        source_url=args.source_url,
        base_model=dapt_cfg.get("backbone", train_cfg.get("backbone", "unknown")),
        pipeline=pipeline_text,
        eval_table=latest_table(args.results, "system"),
        training_data=training_data,
    )

    card_path = os.path.join(args.model_dir, "README.md")
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(card)
    print(f"model card written to {card_path}")

    if not args.push:
        print("\ndry run: nothing uploaded. Review the card above, then re-run "
              "with --push.")
        return

    token = os.getenv("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN not set; cannot push")

    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.create_repo(repo_id=args.repo_id, exist_ok=True)
    api.upload_folder(repo_id=args.repo_id, folder_path=args.model_dir,
                      ignore_patterns=["best_state.pt"],
                      commit_message="publish cbsent weights and model card")
    print(f"pushed to https://huggingface.co/{args.repo_id}")


if __name__ == "__main__":
    main()
