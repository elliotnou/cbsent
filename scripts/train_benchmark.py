"""Fine-tune the adapted ModernBERT on the Trillion Dollar Words benchmark.

Training data is the benchmark's own train split (Shah, Paturi & Chava
2023, CC BY-NC 4.0), optionally extended with Bank of Canada rate
announcement sentences from this project's corpus, labelled under the
same hawkish/dovish/neutral scheme. Evaluation is the benchmark's
held-out test split, untouched during training and model selection; a
seeded stratified slice of the train split serves as validation.

The BoC extension takes only sentences published before this project's
holdout cut (2025-08-01) and prefers human labels where they exist,
falling back to the LLM bootstrap; provenance counts are recorded.

Usage:
    python scripts/train_benchmark.py [--backbone export/modernbert-cb-dapt]
                                      [--boc-sentences 1200] [--seed 20250811]
"""

import argparse
import csv
import json
import os
import random
import subprocess
import sys
from collections import Counter
from datetime import date

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sklearn.metrics import accuracy_score, classification_report, f1_score

from cbsent.ingest import db

# The benchmark's label vocabulary, per its dataset card.
ID2LABEL = {0: "dovish", 1: "hawkish", 2: "neutral"}
LABEL2ID = {v: k for k, v in ID2LABEL.items()}

BENCH_DIR = "data/benchmark"
MAX_LEN = 128


def load_split(name):
    with open(os.path.join(BENCH_DIR, f"{name}.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [r["sentence"] for r in rows], [int(r["label"]) for r in rows]


def load_boc_extension(n: int, cut_date: str, seed: int):
    """BoC rate announcement sentences with stance labels, training window only."""
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.text, coalesce(h.stance, l.stance) AS stance,
                   (h.sentence_id IS NOT NULL) AS is_human
            FROM sentences s
            JOIN documents d ON s.document_id = d.id
            LEFT JOIN labels h ON h.sentence_id = s.id AND h.source = 'human'
            LEFT JOIN labels l ON l.sentence_id = s.id AND l.source = 'llm'
            WHERE d.bank = 'BOC' AND d.doc_type = 'rate_announcement'
              AND s.published_at < %s
              AND coalesce(h.stance, l.stance) IS NOT NULL
            ORDER BY s.id
            """,
            (cut_date,),
        )
        rows = cur.fetchall()
    rng = random.Random(seed)
    rng.shuffle(rows)
    rows = rows[:n]
    texts = [r[0] for r in rows]
    labels = [LABEL2ID[r[1]] for r in rows]
    n_human = sum(1 for r in rows if r[2])
    return texts, labels, n_human


class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, i):
        enc = self.tokenizer(self.texts[i], max_length=MAX_LEN,
                             padding="max_length", truncation=True,
                             return_tensors="pt")
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "label": torch.tensor(self.labels[i]),
        }


def evaluate(model, loader, device):
    model.eval()
    trues, preds = [], []
    with torch.no_grad():
        for batch in loader:
            logits = model(input_ids=batch["input_ids"].to(device),
                           attention_mask=batch["attention_mask"].to(device)).logits
            trues.extend(batch["label"].tolist())
            preds.extend(logits.argmax(dim=-1).cpu().tolist())
    return trues, preds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backbone", default="export/modernbert-cb-dapt")
    parser.add_argument("--boc-sentences", type=int, default=1200,
                        help="0 disables the extension")
    parser.add_argument("--cut-date", default="2025-08-01")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--seed", type=int, default=20250811)
    parser.add_argument("--val-fraction", type=float, default=0.1)
    parser.add_argument("--out", default="export/cbsent-bench")
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    train_texts, train_labels = load_split("train")
    test_texts, test_labels = load_split("test")
    print(f"benchmark: {len(train_texts)} train / {len(test_texts)} test")

    n_human = 0
    if args.boc_sentences > 0:
        boc_texts, boc_labels, n_human = load_boc_extension(
            args.boc_sentences, args.cut_date, args.seed
        )
        print(f"BoC extension: {len(boc_texts)} sentences "
              f"({n_human} human-labelled), {Counter(ID2LABEL[l] for l in boc_labels)}")
        train_texts = train_texts + boc_texts
        train_labels = train_labels + boc_labels

    # Seeded stratified validation slice out of the training pool.
    rng = random.Random(args.seed)
    by_class = {}
    for i, l in enumerate(train_labels):
        by_class.setdefault(l, []).append(i)
    val_idx = set()
    for l, idxs in by_class.items():
        rng.shuffle(idxs)
        val_idx.update(idxs[: max(1, int(len(idxs) * args.val_fraction))])
    tr = [i for i in range(len(train_texts)) if i not in val_idx]
    va = sorted(val_idx)
    print(f"train {len(tr)} / val {len(va)}")

    tokenizer = AutoTokenizer.from_pretrained(args.backbone)
    # bf16 on MPS: full-precision ModernBERT hits the slow kernel path
    # measured in RESULTS.md. Test inference happens in fp32 on CPU.
    dtype = torch.bfloat16 if device.type == "mps" else torch.float32
    model = AutoModelForSequenceClassification.from_pretrained(
        args.backbone, num_labels=3,
        id2label=ID2LABEL, label2id=LABEL2ID, dtype=dtype,
    )
    model.to(device)

    make = lambda idx: TextDataset([train_texts[i] for i in idx],
                                   [train_labels[i] for i in idx], tokenizer)
    g = torch.Generator().manual_seed(args.seed)
    train_dl = DataLoader(make(tr), batch_size=args.batch_size, shuffle=True,
                          generator=g)
    val_dl = DataLoader(make(va), batch_size=64)
    test_dl = DataLoader(TextDataset(test_texts, test_labels, tokenizer),
                         batch_size=64)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr,
                                  weight_decay=0.01)
    criterion = nn.CrossEntropyLoss()

    best_val = -1.0
    best_epoch = 0
    os.makedirs(args.out, exist_ok=True)
    state_path = os.path.join(args.out, "best_state.pt")

    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for batch in train_dl:
            logits = model(input_ids=batch["input_ids"].to(device),
                           attention_mask=batch["attention_mask"].to(device)).logits
            loss = criterion(logits, batch["label"].to(device))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            optimizer.zero_grad()
            total += loss.item() * batch["label"].size(0)
        vt, vp = evaluate(model, val_dl, device)
        val_f1 = f1_score(vt, vp, average="weighted")
        print(f"epoch {epoch}/{args.epochs}  loss={total/len(tr):.4f}  "
              f"val_weighted_f1={val_f1:.4f}")
        if val_f1 > best_val:
            best_val = val_f1
            best_epoch = epoch
            torch.save(model.state_dict(), state_path)

    model.load_state_dict(torch.load(state_path, weights_only=True))
    # Test-set inference in fp32 on CPU for reproducibility, as everywhere else.
    model.float()
    model.to("cpu")
    tt, tp = evaluate(model, test_dl, torch.device("cpu"))
    weighted = f1_score(tt, tp, average="weighted")
    macro = f1_score(tt, tp, average="macro")
    acc = accuracy_score(tt, tp)
    print(f"\nTEST weighted F1 {weighted:.4f}  macro F1 {macro:.4f}  acc {acc:.4f}")
    print(classification_report(tt, tp, target_names=[ID2LABEL[i] for i in range(3)],
                                zero_division=0))

    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    os.remove(state_path)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    config = {
        "seed": args.seed,
        "backbone": args.backbone,
        "benchmark": "gtfintechlab/fomc_communication (CC BY-NC 4.0)",
        "train_size": len(tr),
        "val_size": len(va),
        "test_size": len(test_texts),
        "boc_extension": args.boc_sentences if args.boc_sentences > 0 else 0,
        "boc_human_labelled": n_human,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "best_epoch": best_epoch,
        "best_val_weighted_f1": round(best_val, 4),
        "test_weighted_f1": round(weighted, 4),
        "test_macro_f1": round(macro, 4),
        "test_accuracy": round(acc, 4),
        "git_commit": commit,
        "train_device": str(device),
        "test_device": "cpu",
    }
    with open(os.path.join(args.out, "config.json"), "w") as f:
        json.dump(config, f, indent=2)

    if not args.no_results_append:
        entry = (
            f"\n## TDW benchmark fine-tune, seed {args.seed} "
            f"({date.today().isoformat()})\n\n"
            f"- command: `python scripts/train_benchmark.py --backbone {args.backbone}"
            f" --boc-sentences {args.boc_sentences} --seed {args.seed}`\n"
            f"- git commit: `{commit}`\n"
            f"- benchmark: Trillion Dollar Words (gtfintechlab/fomc_communication),"
            f" official train/test split, test untouched until this evaluation\n"
            f"- BoC extension: {args.boc_sentences} sentences"
            f" ({n_human} human-labelled), training window only\n"
            f"- test inference device: cpu\n\n"
            f"| metric | value |\n|---|---|\n"
            f"| weighted F1 (benchmark standard) | {weighted:.4f} |\n"
            f"| macro F1 | {macro:.4f} |\n"
            f"| accuracy | {acc:.4f} |\n"
            f"| best epoch (val weighted F1 {best_val:.4f}) | {best_epoch} |\n"
        )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("appended to RESULTS.md")


if __name__ == "__main__":
    main()
