"""Build the unlabelled domain-adaptation corpus.

Adds to the core corpus:
  - Fed speeches and testimony from the official JSON feeds (2006 onward)
  - historical FOMC statements and minutes from the per-year archive pages
  - Bank of Canada speeches from the press listing

Everything lands in the same documents/sentences tables with exact (or
conservatively late) publication timestamps, and is idempotent by URL.
The labelled stance dataset is unaffected; these documents exist for
masked-language-model adaptation and the yield study.

Usage:
    python scripts/ingest_expanded.py [--earliest 2006-01-01]
                                      [--history-years 2011-2020]
"""

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cbsent.ingest import boc_speeches, db, fed, fed_feeds, fed_history
from cbsent.segment import segment_sentences


def parse_year_range(spec: str):
    lo, hi = spec.split("-")
    return range(int(lo), int(hi) + 1)


def insert_all(conn, known, jobs, fetcher, fixup=None):
    inserted = skipped = failed = 0
    for job in jobs:
        if job.url in known:
            skipped += 1
            continue
        doc_dict = fetcher(job)
        if doc_dict is None:
            failed += 1
            continue
        if fixup:
            doc_dict = fixup(job, doc_dict)
        doc = db.Document(**doc_dict)
        sentences = segment_sentences(doc.content)
        if len(sentences) < 3:
            failed += 1
            continue
        if db.insert_document(conn, doc, sentences):
            inserted += 1
            known.add(doc.url)
            if inserted % 50 == 0:
                print(f"  {inserted} inserted...")
        else:
            skipped += 1
    return inserted, skipped, failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--earliest", default="2006-01-01")
    parser.add_argument("--history-years", default="2011-2020")
    parser.add_argument("--cache-dir", default="data/raw")
    parser.add_argument("--sources", default="history,speeches,testimony,boc",
                        help="comma list from: history, speeches, testimony, boc")
    args = parser.parse_args()

    earliest = datetime.date.fromisoformat(args.earliest)
    sources = {s.strip() for s in args.sources.split(",")}

    # Discovery before the database connection opens, as in ingest.py.
    jobs = {}
    if "history" in sources:
        jobs["history"] = fed_history.list_releases(
            parse_year_range(args.history_years), args.cache_dir
        )
        print(f"historical Fed releases: {len(jobs['history'])}")
    if "speeches" in sources:
        jobs["speeches"] = fed_feeds.list_items("speech", args.cache_dir, earliest)
        print(f"Fed speeches: {len(jobs['speeches'])}")
    if "testimony" in sources:
        jobs["testimony"] = fed_feeds.list_items("testimony", args.cache_dir, earliest)
        print(f"Fed testimony: {len(jobs['testimony'])}")
    if "boc" in sources:
        jobs["boc"] = boc_speeches.list_speeches(args.cache_dir, earliest)
        print(f"BoC speeches: {len(jobs['boc'])}")

    def fix_history_ts(release, doc_dict):
        if release.doc_type == "statement":
            doc_dict["published_at"] = fed_history.statement_release_ts(
                release.release_date
            )
        return doc_dict

    with db.connect() as conn:
        db.ensure_schema(conn)
        known = db.existing_urls(conn)
        totals = [0, 0, 0]

        for name, batch in jobs.items():
            if name == "history":
                fetcher = lambda r: fed.fetch_document(r, args.cache_dir)
                result = insert_all(conn, known, batch, fetcher, fix_history_ts)
            elif name in ("speeches", "testimony"):
                fetcher = lambda i: fed_feeds.fetch_document(i, args.cache_dir)
                result = insert_all(conn, known, batch, fetcher)
            else:
                fetcher = lambda s: boc_speeches.fetch_document(s, args.cache_dir)
                result = insert_all(conn, known, batch, fetcher)
            print(f"{name}: {result[0]} inserted, {result[1]} skipped, {result[2]} failed")
            totals = [a + b for a, b in zip(totals, result)]

        print(f"\ntotal: {totals[0]} inserted, {totals[1]} skipped, {totals[2]} failed")
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM sentences")
            print(f"sentences in corpus: {cur.fetchone()[0]}")


if __name__ == "__main__":
    main()
