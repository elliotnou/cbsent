"""Export the corpus to CSV snapshots under data/.

The committed snapshots let anyone reproduce every downstream number
without database access or re-scraping.

Usage:
    python scripts/export_snapshot.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cbsent.ingest import db

OUT_DIR = "data"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, bank, doc_type, url, title, published_at, meeting_date
            FROM documents ORDER BY published_at, id
            """
        )
        doc_rows = cur.fetchall()
        with open(os.path.join(OUT_DIR, "documents.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "bank", "doc_type", "url", "title", "published_at", "meeting_date"])
            w.writerows(doc_rows)

        # The sentence snapshot covers the core corpus that labels and
        # evaluations run on. Speeches and testimony exist for MLM
        # adaptation only, are an order of magnitude larger, and are
        # reproducible from scripts/ingest_expanded.py plus the fetch
        # cache, so they stay out of git.
        cur.execute(
            """
            SELECT s.id, s.document_id, s.seq, s.text, s.published_at
            FROM sentences s JOIN documents d ON s.document_id = d.id
            WHERE d.doc_type IN ('statement', 'minutes', 'rate_announcement')
            ORDER BY s.document_id, s.seq
            """
        )
        sent_rows = cur.fetchall()
        with open(os.path.join(OUT_DIR, "sentences.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "document_id", "seq", "text", "published_at"])
            w.writerows(sent_rows)

    print(f"wrote {len(doc_rows)} documents, {len(sent_rows)} sentences to {OUT_DIR}/")


if __name__ == "__main__":
    main()
