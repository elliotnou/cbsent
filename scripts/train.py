"""Train the cbsent model on the labelled corpus.

Chronological discipline: training uses only sentences published before
--cut-date; the year starting at --cut-date is never seen. Validation for
early stopping is the final --val-months of the training window, so no
random splits exist anywhere.

Labels resolve as human first, LLM bootstrap otherwise; provenance counts
are stored in the exported config.

Usage:
    python scripts/train.py [--cut-date 2025-08-01] [--no-negation-markers]
                            [--epochs 8] [--export-dir export/cbsent]
"""

import argparse
import json
import os
import random
import subprocess
import sys
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sklearn.metrics import f1_score

from cbsent.ingest import db
from cbsent.model import (
    CBSentModel, MAX_SEQ_LEN, STANCE_LABELS, TOPIC_LABELS,
    build_tokenizer, pick_device,
)
from cbsent.negation import mark_cues

SEED = 20250811


def set_seeds():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)


def load_labelled(conn, cut_date: str):
    """Sentences published before cut_date with resolved labels."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.text, s.published_at,
                   coalesce(h.stance, l.stance) AS stance,
                   coalesce(h.topic,  l.topic)  AS topic,
                   (h.sentence_id IS NOT NULL)  AS is_human
            FROM sentences s
            LEFT JOIN labels h ON h.sentence_id = s.id AND h.source = 'human'
            LEFT JOIN labels l ON l.sentence_id = s.id AND l.source = 'llm'
            WHERE s.published_at < %s
              AND coalesce(h.stance, l.stance) IS NOT NULL
            ORDER BY s.published_at, s.id
            """,
            (cut_date,),
        )
        return cur.fetchall()


class LabelledDataset(Dataset):
    def __init__(self, rows, tokenizer, use_markers: bool):
        self.texts = [mark_cues(r[0]) if use_markers else r[0] for r in rows]
        self.stances = [STANCE_LABELS.index(r[2]) for r in rows]
        self.topics = [TOPIC_LABELS.index(r[3]) if r[3] in TOPIC_LABELS else -100
                       for r in rows]
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, i):
        enc = self.tokenizer(
            self.texts[i], max_length=MAX_SEQ_LEN, padding="max_length",
            truncation=True, return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "stance": torch.tensor(self.stances[i]),
            "topic": torch.tensor(self.topics[i]),
        }


def evaluate(model, loader, device):
    model.eval()
    true_s, pred_s = [], []
    with torch.no_grad():
        for batch in loader:
            ids = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            stance_logits, _ = model(ids, mask)
            true_s.extend(batch["stance"].tolist())
            pred_s.extend(stance_logits.argmax(dim=-1).cpu().tolist())
    return f1_score(true_s, pred_s, average="macro")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cut-date", default="2025-08-01")
    parser.add_argument("--val-months", type=int, default=6)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--no-negation-markers", action="store_true")
    parser.add_argument("--export-dir", default="export/cbsent")
    args = parser.parse_args()

    set_seeds()
    use_markers = not args.no_negation_markers
    device = pick_device()
    print(f"device: {device}, negation markers: {use_markers}")

    with db.connect() as conn:
        rows = load_labelled(conn, args.cut_date)
    if len(rows) < 100:
        raise SystemExit(f"only {len(rows)} labelled sentences before {args.cut_date}")

    # Chronological validation: last N months of the training window.
    cut = datetime.fromisoformat(args.cut_date)
    months_since_epoch = cut.year * 12 + (cut.month - 1) - args.val_months
    val_start = cut.replace(year=months_since_epoch // 12,
                            month=months_since_epoch % 12 + 1)
    train_rows = [r for r in rows if r[1].replace(tzinfo=None) < val_start]
    val_rows = [r for r in rows if r[1].replace(tzinfo=None) >= val_start]
    n_human = sum(1 for r in rows if r[4])
    print(f"train: {len(train_rows)}  val: {len(val_rows)} "
          f"(val from {val_start:%Y-%m-%d}, {n_human} human labels)")

    tokenizer = build_tokenizer(use_markers)
    train_ds = LabelledDataset(train_rows, tokenizer, use_markers)
    val_ds = LabelledDataset(val_rows, tokenizer, use_markers)

    g = torch.Generator().manual_seed(SEED)
    train_dl = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, generator=g)
    val_dl = DataLoader(val_ds, batch_size=args.batch_size)

    model = CBSentModel()
    if use_markers:
        model.distilbert.resize_token_embeddings(len(tokenizer))
    model.to(device)

    # Inverse-frequency stance weights from the training window only.
    counts = np.bincount(train_ds.stances, minlength=len(STANCE_LABELS))
    weights = torch.tensor(counts.sum() / np.maximum(counts, 1),
                           dtype=torch.float).to(device)
    weights = weights / weights.mean()
    stance_criterion = nn.CrossEntropyLoss(weight=weights)
    topic_criterion = nn.CrossEntropyLoss(ignore_index=-100)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    best_f1 = -1.0
    best_epoch = 0
    os.makedirs(args.export_dir, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for batch in train_dl:
            ids = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            stance_logits, topic_logits = model(ids, mask)
            loss = stance_criterion(stance_logits, batch["stance"].to(device))
            loss = loss + topic_criterion(topic_logits, batch["topic"].to(device))
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += loss.item() * ids.size(0)

        val_f1 = evaluate(model, val_dl, device)
        print(f"epoch {epoch}/{args.epochs}  loss={total/len(train_ds):.4f}  "
              f"val_stance_macro_f1={val_f1:.4f}")

        if val_f1 > best_f1:
            best_f1 = val_f1
            best_epoch = epoch
            torch.save(model.state_dict(), os.path.join(args.export_dir, "model.pt"))

    tokenizer.save_pretrained(os.path.join(args.export_dir, "tokenizer"))
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    config = {
        "seed": SEED,
        "cut_date": args.cut_date,
        "val_start": val_start.strftime("%Y-%m-%d"),
        "use_negation_markers": use_markers,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "max_seq_len": MAX_SEQ_LEN,
        "backbone": "distilbert-base-uncased",
        "stance_labels": STANCE_LABELS,
        "topic_labels": TOPIC_LABELS,
        "train_sentences": len(train_rows),
        "val_sentences": len(val_rows),
        "human_labelled": n_human,
        "best_epoch": best_epoch,
        "best_val_macro_f1": round(best_f1, 4),
        "git_commit": commit,
        "device": str(device),
    }
    with open(os.path.join(args.export_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
    print(f"\nbest epoch {best_epoch}, val macro-F1 {best_f1:.4f}")
    print(f"exported to {args.export_dir}")


if __name__ == "__main__":
    main()
