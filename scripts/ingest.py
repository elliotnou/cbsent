"""Build the research corpus: scrape, segment, and load into PostgreSQL.

Usage:
    python scripts/ingest.py [--earliest YYYY-MM-DD] [--cache-dir data/raw]

Idempotent: documents already in the database (by URL) are skipped, and all
fetched pages are cached on disk, so re-runs are cheap and reproducible.
"""

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cbsent.ingest import boc, db, fed
from cbsent.segment import segment_sentences

DEFAULT_EARLIEST = "2021-08-01"


def main():
    parser = argparse.ArgumentParser(description="Ingest Fed and BoC documents")
    parser.add_argument("--earliest", default=DEFAULT_EARLIEST)
    parser.add_argument("--cache-dir", default="data/raw")
    args = parser.parse_args()

    earliest = datetime.date.fromisoformat(args.earliest)

    # Discovery runs before the database connection is opened: probing
    # candidate announcement dates can take many minutes on a cold cache,
    # long enough for a managed Postgres to drop an idle connection.
    fed_releases = fed.list_releases(args.cache_dir, earliest)
    boc_releases = boc.list_releases(args.cache_dir, earliest)
    print(f"Fed releases listed: {len(fed_releases)}")
    print(f"BoC releases listed: {len(boc_releases)}")

    with db.connect() as conn:
        db.ensure_schema(conn)
        known = db.existing_urls(conn)

        inserted = skipped = failed = 0
        jobs = [(fed, r) for r in fed_releases] + [(boc, r) for r in boc_releases]
        for module, release in jobs:
            if release.url in known:
                skipped += 1
                continue
            doc_dict = module.fetch_document(release, args.cache_dir)
            if doc_dict is None:
                print(f"failed to extract: {release.url}")
                failed += 1
                continue
            doc = db.Document(**doc_dict)
            sentence_texts = segment_sentences(doc.content)
            if not sentence_texts:
                print(f"no sentences: {release.url}")
                failed += 1
                continue
            doc_id = db.insert_document(conn, doc, sentence_texts)
            if doc_id:
                inserted += 1
                print(f"inserted [{doc.bank} {doc.doc_type}] {doc.published_at:%Y-%m-%d %H:%M %Z} "
                      f"({len(sentence_texts)} sentences)")
            else:
                skipped += 1

        print(f"\ndone: {inserted} inserted, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
