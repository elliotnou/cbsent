"""
Training pipeline for multi-task DistilBERT sentiment model.

Distillation approach: uses GPT-4o-mini labels already stored in the
transcript_sentences table as ground-truth targets so the smaller
DistilBERT model learns to replicate them.

Outputs:
    backend/analysis/model/export/
        model.pt          – state dict
        tokenizer/        – saved HF tokenizer
        metadata.json     – label maps, training metrics
"""

import os
import json
import argparse
import numpy as np
import psycopg2
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import DistilBertTokenizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_absolute_error
from dotenv import load_dotenv

from distilbert_model import MultiTaskDistilBERT, TOPIC_LABELS, normalize_topic

# .env lives in backend/ — resolve from this file's location
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------
BATCH_SIZE = 16
LEARNING_RATE = 2e-5
EPOCHS = 10
MAX_SEQ_LEN = 128
SCORE_LOSS_WEIGHT = 1.0
TOPIC_LOSS_WEIGHT = 1.0
GRAD_CLIP = 1.0

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "export")


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
class SentenceDataset(Dataset):
    """Wraps tokenised sentences with regression + classification targets."""

    def __init__(self, texts, scores, topic_ids, tokenizer, max_len=MAX_SEQ_LEN):
        self.texts = texts
        self.scores = scores
        self.topic_ids = topic_ids
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "score": torch.tensor(self.scores[idx], dtype=torch.float),
            "topic_id": torch.tensor(self.topic_ids[idx], dtype=torch.long),
        }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_training_data():
    """Pull GPT-labelled sentences from the database."""
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sentence_text, stance_score, topic
        FROM transcript_sentences
        WHERE sentence_text IS NOT NULL
          AND stance_score IS NOT NULL
          AND topic IS NOT NULL
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    texts, scores, topics = [], [], []
    topic_to_id = {t: i for i, t in enumerate(TOPIC_LABELS)}

    skipped = 0
    for text, score, topic in rows:
        canonical = normalize_topic(topic)
        if canonical is None:
            skipped += 1
            continue
        texts.append(text)
        scores.append(float(score))
        topics.append(topic_to_id[canonical])

    print(f"Loaded {len(texts)} labelled sentences from database (skipped {skipped})")
    return texts, scores, topics


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # ---- data ----
    texts, scores, topic_ids = load_training_data()
    if len(texts) < 10:
        raise RuntimeError(
            f"Only {len(texts)} samples found — need more labelled data to train."
        )

    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")

    (
        train_texts, val_texts,
        train_scores, val_scores,
        train_topics, val_topics,
    ) = train_test_split(
        texts, scores, topic_ids,
        test_size=0.2,
        random_state=42,
        stratify=topic_ids,
    )

    train_ds = SentenceDataset(train_texts, train_scores, train_topics, tokenizer)
    val_ds = SentenceDataset(val_texts, val_scores, val_topics, tokenizer)
    train_dl = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_dl = DataLoader(val_ds, batch_size=args.batch_size)

    # ---- model ----
    model = MultiTaskDistilBERT().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    score_criterion = nn.MSELoss()
    topic_criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_metrics = {}

    for epoch in range(1, args.epochs + 1):
        # --- train ---
        model.train()
        train_loss = 0.0
        for batch in train_dl:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            target_score = batch["score"].to(device)
            target_topic = batch["topic_id"].to(device)

            pred_score, pred_topic_logits = model(input_ids, attention_mask)

            loss_score = score_criterion(pred_score, target_score)
            loss_topic = topic_criterion(pred_topic_logits, target_topic)
            loss = SCORE_LOSS_WEIGHT * loss_score + TOPIC_LOSS_WEIGHT * loss_topic

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            optimizer.step()

            train_loss += loss.item() * input_ids.size(0)

        train_loss /= len(train_ds)

        # --- validate ---
        model.eval()
        val_loss = 0.0
        all_true_scores, all_pred_scores = [], []
        all_true_topics, all_pred_topics = [], []

        with torch.no_grad():
            for batch in val_dl:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                target_score = batch["score"].to(device)
                target_topic = batch["topic_id"].to(device)

                pred_score, pred_topic_logits = model(input_ids, attention_mask)

                loss_score = score_criterion(pred_score, target_score)
                loss_topic = topic_criterion(pred_topic_logits, target_topic)
                loss = SCORE_LOSS_WEIGHT * loss_score + TOPIC_LOSS_WEIGHT * loss_topic
                val_loss += loss.item() * input_ids.size(0)

                all_true_scores.extend(target_score.cpu().numpy())
                all_pred_scores.extend(pred_score.cpu().numpy())
                all_true_topics.extend(target_topic.cpu().numpy())
                all_pred_topics.extend(pred_topic_logits.argmax(dim=1).cpu().numpy())

        val_loss /= len(val_ds)
        mae = mean_absolute_error(all_true_scores, all_pred_scores)

        print(
            f"Epoch {epoch}/{args.epochs}  "
            f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  MAE={mae:.4f}"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_metrics = {"mae": mae, "val_loss": val_loss, "epoch": epoch}
            # save checkpoint
            os.makedirs(EXPORT_DIR, exist_ok=True)
            torch.save(model.state_dict(), os.path.join(EXPORT_DIR, "model.pt"))

    # ---- final report ----
    print("\n=== Best Model (epoch {}) ===".format(best_metrics.get("epoch", "?")))
    print(f"  MAE:      {best_metrics.get('mae', '?'):.4f}")
    print(f"  Val Loss: {best_metrics.get('val_loss', '?'):.4f}")

    print("\n=== Classification Report (last epoch) ===")
    print(
        classification_report(
            all_true_topics,
            all_pred_topics,
            target_names=TOPIC_LABELS,
            zero_division=0,
        )
    )

    # ---- save tokenizer + metadata ----
    tokenizer.save_pretrained(os.path.join(EXPORT_DIR, "tokenizer"))
    metadata = {
        "topic_labels": TOPIC_LABELS,
        "max_seq_len": MAX_SEQ_LEN,
        "best_epoch": best_metrics.get("epoch"),
        "best_mae": round(best_metrics.get("mae", 0), 4),
        "best_val_loss": round(best_metrics.get("val_loss", 0), 4),
        "train_samples": len(train_ds),
        "val_samples": len(val_ds),
    }
    with open(os.path.join(EXPORT_DIR, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"\nModel artefacts saved to {EXPORT_DIR}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train multi-task DistilBERT")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=LEARNING_RATE)
    args = parser.parse_args()
    train(args)
