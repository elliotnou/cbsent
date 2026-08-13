"""Domain-adaptive pretraining: ModernBERT MLM on the central bank corpus.

Continues masked-language-model training of ModernBERT-base on every
document in the corpus (statements, minutes, rate announcements, speeches,
testimony). Documents are tokenized and packed into fixed-length blocks so
no compute is spent on padding. The adapted backbone is saved in Hugging
Face format for scripts/train_benchmark.py to build on.

Runs on Apple MPS. MPS training is not bit-reproducible (see RESULTS.md);
the saved weights are the artefact of record.

Usage:
    python scripts/pretrain_dapt.py [--epochs 2] [--block-size 128]
                                    [--out export/modernbert-cb-dapt]
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cbsent.ingest import db

SEED = 20250811


def set_seeds():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)


def load_corpus(conn):
    """Document texts plus the sentence count, for the record."""
    with conn.cursor() as cur:
        cur.execute("SELECT content FROM documents ORDER BY id")
        texts = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT count(*) FROM sentences")
        n_sentences = cur.fetchone()[0]
    return texts, n_sentences


def pack_blocks(texts, tokenizer, block_size: int):
    """Tokenize documents and pack token ids into contiguous blocks."""
    blocks = []
    buffer = []
    sep = tokenizer.sep_token_id
    for text in texts:
        ids = tokenizer(text, add_special_tokens=False)["input_ids"]
        buffer.extend(ids + [sep])
        while len(buffer) >= block_size:
            blocks.append(buffer[:block_size])
            buffer = buffer[block_size:]
    return torch.tensor(blocks, dtype=torch.long)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backbone", default="answerdotai/ModernBERT-base")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--block-size", type=int, default=128)
    parser.add_argument("--mlm-probability", type=float, default=0.30)
    parser.add_argument("--val-fraction", type=float, default=0.02)
    parser.add_argument("--out", default="export/modernbert-cb-dapt")
    parser.add_argument("--dtype", default="bf16", choices=["bf16", "fp32"])
    args = parser.parse_args()

    from transformers import (
        AutoModelForMaskedLM, AutoTokenizer, DataCollatorForLanguageModeling,
    )

    set_seeds()
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"device: {device}")

    with db.connect() as conn:
        texts, n_sentences = load_corpus(conn)
    print(f"documents: {len(texts)}, sentences: {n_sentences}")

    tokenizer = AutoTokenizer.from_pretrained(args.backbone)
    blocks = pack_blocks(texts, tokenizer, args.block_size)
    print(f"packed blocks: {len(blocks)} x {args.block_size} tokens "
          f"({blocks.numel()/1e6:.1f}M tokens)")

    g = torch.Generator().manual_seed(SEED)
    perm = torch.randperm(len(blocks), generator=g)
    n_val = max(64, int(len(blocks) * args.val_fraction))
    val_blocks = blocks[perm[:n_val]]
    train_blocks = blocks[perm[n_val:]]

    collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer, mlm_probability=args.mlm_probability,
    )

    # Full-precision ModernBERT hits a pathologically slow kernel path on
    # MPS (about 50 s/step at sequence length 128, roughly 17x slower than
    # bfloat16; measured in RESULTS.md). Training runs in bf16 end to end
    # and the adapted weights are cast back to fp32 for export.
    dtype = torch.bfloat16 if args.dtype == "bf16" else torch.float32
    model = AutoModelForMaskedLM.from_pretrained(args.backbone, dtype=dtype)
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr,
                                  weight_decay=0.01)
    steps_per_epoch = (len(train_blocks) + args.batch_size - 1) // args.batch_size
    total_steps = steps_per_epoch * args.epochs
    warmup = max(50, total_steps // 20)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer,
        lambda s: min(1.0, s / warmup) * max(
            0.0, (total_steps - s) / max(1, total_steps - warmup)
        ),
    )
    print(f"steps per epoch: {steps_per_epoch}, total: {total_steps}")

    def masked_batch(idx_tensor):
        rows = [{"input_ids": row.tolist()} for row in idx_tensor]
        batch = collator(rows)
        return batch["input_ids"].to(device), batch["labels"].to(device)

    @torch.no_grad()
    def val_loss():
        model.eval()
        losses = []
        for i in range(0, len(val_blocks), args.batch_size):
            ids, labels = masked_batch(val_blocks[i:i + args.batch_size])
            out = model(input_ids=ids, labels=labels)
            losses.append(out.loss.item())
        model.train()
        return sum(losses) / len(losses)

    print(f"initial val MLM loss: {val_loss():.4f}")

    model.train()
    step = 0
    t0 = time.time()
    for epoch in range(1, args.epochs + 1):
        order = torch.randperm(len(train_blocks), generator=g)
        running = 0.0
        for i in range(0, len(train_blocks), args.batch_size):
            ids, labels = masked_batch(train_blocks[order[i:i + args.batch_size]])
            out = model(input_ids=ids, labels=labels)
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            running += out.loss.item()
            step += 1
            if step % 200 == 0:
                rate = step / (time.time() - t0)
                remaining = (total_steps - step) / rate / 60
                print(f"step {step}/{total_steps}  loss {running/200:.4f}  "
                      f"{rate:.2f} it/s  ~{remaining:.0f} min left")
                running = 0.0
        print(f"epoch {epoch}/{args.epochs} done, val MLM loss: {val_loss():.4f}")

    final_val = val_loss()
    os.makedirs(args.out, exist_ok=True)
    model.float()
    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    config = {
        "seed": SEED,
        "backbone": args.backbone,
        "documents": len(texts),
        "corpus_sentences": n_sentences,
        "blocks": len(blocks),
        "block_size": args.block_size,
        "tokens_millions": round(blocks.numel() / 1e6, 1),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "mlm_probability": args.mlm_probability,
        "train_dtype": args.dtype,
        "final_val_mlm_loss": round(final_val, 4),
        "git_commit": commit,
        "device": str(device),
    }
    with open(os.path.join(args.out, "dapt_config.json"), "w") as f:
        json.dump(config, f, indent=2)
    print(f"\nfinal val MLM loss: {final_val:.4f}")
    print(f"saved adapted backbone to {args.out}")


if __name__ == "__main__":
    main()
