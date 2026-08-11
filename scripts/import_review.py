"""Load reviewed labels from the HTML reviewer's CSV export.

Usage:
    python scripts/import_review.py reviewed.csv
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from psycopg2.extras import execute_values

from cbsent.ingest import db
from cbsent.labels import STANCES, TOPICS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    args = parser.parse_args()

    rows, bad = [], 0
    with open(args.csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stance = (row.get("stance") or "").strip()
            topic = (row.get("topic") or "").strip()
            if stance not in STANCES or topic not in TOPICS:
                bad += 1
                continue
            rows.append((int(row["sentence_id"]), "human", stance, topic))

    if not rows:
        raise SystemExit("no valid rows found")

    with db.connect() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO labels (sentence_id, source, stance, topic)
            VALUES %s
            ON CONFLICT (sentence_id, source)
            DO UPDATE SET stance = EXCLUDED.stance, topic = EXCLUDED.topic
            """,
            rows,
            page_size=500,
        )
        conn.commit()
        cur.execute("SELECT count(*) FROM labels WHERE source = 'human'")
        total = cur.fetchone()[0]

    print(f"imported {len(rows)} human labels ({bad} skipped)")
    print(f"human labels in database: {total}")


if __name__ == "__main__":
    main()
