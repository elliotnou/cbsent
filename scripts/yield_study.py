"""Document hawkishness vs same-day 2-year Treasury yield moves.

For every FOMC statement and minutes release in the corpus, scores the
document with the benchmark fine-tune (mean over sentences of
P(hawkish) - P(dovish)) and pairs it with the same-day change in the
2-year constant-maturity Treasury yield (FRED series DGS2, close over
prior close). Reports Pearson and Spearman correlations for the score
level and for its change since the previous release of the same type.

The 2-year point is the standard maturity for measuring monetary policy
surprises; DGS2 is daily, so intraday release-time differences across the
sample never enter the number.

Usage:
    python scripts/yield_study.py [--model-dir export/cbsent-bench]
                                  [--start 2011-01-01]
"""

import argparse
import csv
import datetime
import math
import os
import subprocess
import sys
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import torch

from cbsent.ingest import db
from cbsent.segment import segment_sentences

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2&cosd={start}"
FX_CACHE = "data/fx_cache"


def fetch_dgs2(start: str) -> Dict[datetime.date, float]:
    import requests

    os.makedirs(FX_CACHE, exist_ok=True)
    path = os.path.join(FX_CACHE, f"dgs2_{start}.csv")
    if not os.path.exists(path):
        resp = requests.get(FRED_URL.format(start=start), timeout=30)
        resp.raise_for_status()
        with open(path, "w", encoding="utf-8") as f:
            f.write(resp.text)
    out = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            date_key = row.get("observation_date") or row.get("DATE")
            value = row.get("DGS2")
            if not date_key or not value or value == ".":
                continue
            out[datetime.date.fromisoformat(date_key)] = float(value)
    return out


def score_documents(model_dir: str, docs: List[tuple], batch_size: int = 64):
    """Mean P(hawkish)-P(dovish) per document, on CPU."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    hawk = model.config.label2id["hawkish"]
    dove = model.config.label2id["dovish"]

    scores = []
    with torch.no_grad():
        for _, _, _, content in docs:
            sentences = segment_sentences(content)
            if not sentences:
                scores.append(None)
                continue
            vals = []
            for i in range(0, len(sentences), batch_size):
                enc = tokenizer(sentences[i:i + batch_size], max_length=128,
                                padding=True, truncation=True,
                                return_tensors="pt")
                probs = model(**enc).logits.softmax(dim=-1)
                vals.extend((probs[:, hawk] - probs[:, dove]).tolist())
            scores.append(sum(vals) / len(vals))
    return scores


def pearson(x, y):
    x, y = np.asarray(x), np.asarray(y)
    x = x - x.mean()
    y = y - y.mean()
    denom = math.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / denom) if denom else float("nan")


def spearman(x, y):
    rank = lambda v: np.argsort(np.argsort(v)).astype(float)
    return pearson(rank(np.asarray(x)), rank(np.asarray(y)))


def perm_pvalue(x, y, stat, iters=10000, seed=20250811):
    """Two-sided permutation p-value for a correlation statistic."""
    rng = np.random.default_rng(seed)
    observed = abs(stat(x, y))
    y = np.asarray(y)
    hits = 0
    for _ in range(iters):
        if abs(stat(x, rng.permutation(y))) >= observed:
            hits += 1
    return (hits + 1) / (iters + 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default="export/cbsent-bench")
    parser.add_argument("--start", default="2011-01-01")
    parser.add_argument("--doc-types", default="statement,minutes")
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    doc_types = tuple(t.strip() for t in args.doc_types.split(","))
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, doc_type, (published_at AT TIME ZONE 'America/New_York')::date,
                   content
            FROM documents
            WHERE bank = 'FED' AND doc_type = ANY(%s)
              AND published_at >= %s
            ORDER BY published_at
            """,
            (list(doc_types), args.start),
        )
        docs = cur.fetchall()
    print(f"Fed releases ({'+'.join(doc_types)}) since {args.start}: {len(docs)}")

    yields = fetch_dgs2(args.start)
    days = sorted(yields)

    print("scoring documents on cpu...")
    scores = score_documents(args.model_dir, docs)

    rows = []
    for (doc_id, doc_type, day, _), score in zip(docs, scores):
        if score is None or day not in yields:
            continue
        prior = [d for d in days if d < day]
        if not prior:
            continue
        dy = (yields[day] - yields[prior[-1]]) * 100.0  # basis points
        rows.append({"doc_id": doc_id, "doc_type": doc_type, "date": day,
                     "score": score, "dy_bps": dy})

    # Score change since the previous release of the same document type:
    # the new information in a release, not its standing level.
    by_type: Dict[str, List[dict]] = {}
    for r in rows:
        seq = by_type.setdefault(r["doc_type"], [])
        r["score_change"] = r["score"] - seq[-1]["score"] if seq else None
        seq.append(r)

    x_level = [r["score"] for r in rows]
    y_dy = [r["dy_bps"] for r in rows]
    changed = [r for r in rows if r["score_change"] is not None]
    x_change = [r["score_change"] for r in changed]
    y_dy_c = [r["dy_bps"] for r in changed]

    r_level = pearson(x_level, y_dy)
    p_level = perm_pvalue(x_level, y_dy, pearson)
    r_change = pearson(x_change, y_dy_c)
    p_change = perm_pvalue(x_change, y_dy_c, pearson)
    rho_change = spearman(x_change, y_dy_c)

    print(f"\nreleases with score and yield data: {len(rows)}")
    print(f"score level  vs same-day dy: r = {r_level:+.4f} (perm p = {p_level:.4f})")
    print(f"score change vs same-day dy: r = {r_change:+.4f} (perm p = {p_change:.4f}), "
          f"spearman {rho_change:+.4f}, n = {len(changed)}")

    os.makedirs("data", exist_ok=True)
    with open("data/yield_study.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["doc_id", "doc_type", "date",
                                               "score", "score_change", "dy_bps"])
        writer.writeheader()
        writer.writerows(rows)
    print("per-release detail written to data/yield_study.csv")

    if not args.no_results_append:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        entry = (
            f"\n## 2-year yield study ({datetime.date.today().isoformat()})\n\n"
            f"- command: `python scripts/yield_study.py --model-dir {args.model_dir}"
            f" --start {args.start} --doc-types {args.doc_types}`\n"
            f"- git commit: `{commit}`\n"
            f"- releases scored: {len(rows)} Fed ({'+'.join(doc_types)}),"
            f" {args.start} onward\n"
            f"- yield: FRED DGS2 daily close, same-day change over prior"
            f" business day, basis points\n"
            f"- score: mean P(hawkish)-P(dovish) over sentences,"
            f" {args.model_dir}, cpu\n\n"
            f"| relation | Pearson r | permutation p (two-sided) | n |\n"
            f"|---|---|---|---|\n"
            f"| score level vs same-day 2y move | {r_level:+.4f} | {p_level:.4f} | {len(rows)} |\n"
            f"| score change vs same-day 2y move | {r_change:+.4f} | {p_change:.4f} | {len(changed)} |\n"
        )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("appended to RESULTS.md")


if __name__ == "__main__":
    main()
