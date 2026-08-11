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

        cur.execute(
            """
            SELECT id, document_id, seq, text, published_at
            FROM sentences ORDER BY document_id, seq
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
