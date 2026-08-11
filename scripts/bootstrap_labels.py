"""Bootstrap first-pass labels: dictionary + LLM against the codebook.

Selection: every sentence from Fed statements and BoC rate announcements
(the policy-dense documents), plus a deterministic per-document sample
from FOMC minutes to reach the target count. Both labellers run on the
same selection; disagreements feed the human review queue.

Usage:
    python scripts/bootstrap_labels.py [--target 3000] [--llm-model gpt-5-mini]
                                       [--dry-run]
"""

import argparse
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from psycopg2.extras import execute_values

from cbsent import dictionary, llm_label
from cbsent.ingest import db

SEED = 20250811
CACHE_DIR = "data/llm_cache"


def select_sentences(conn, target: int):
    """Deterministic stratified selection, returns [(id, text)]."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.id, s.text, d.doc_type, d.id
            FROM sentences s JOIN documents d ON s.document_id = d.id
            ORDER BY s.id
            """
        )
        rows = cur.fetchall()

    core = [(sid, text) for sid, text, doc_type, _ in rows
            if doc_type in ("statement", "rate_announcement")]
    minutes_by_doc = {}
    for sid, text, doc_type, doc_id in rows:
        if doc_type == "minutes":
            minutes_by_doc.setdefault(doc_id, []).append((sid, text))

    remaining = target - len(core)
    if remaining <= 0 or not minutes_by_doc:
        return core

    rng = random.Random(SEED)
    per_doc = max(1, remaining // len(minutes_by_doc))
    sampled = []
    for doc_id in sorted(minutes_by_doc):
        doc_sents = minutes_by_doc[doc_id]
        k = min(per_doc, len(doc_sents))
        sampled.extend(rng.sample(doc_sents, k))
    rng.shuffle(sampled)
    return core + sampled[:remaining]


def upsert_labels(cur, rows):
    """Batch upsert of (sentence_id, source, stance, topic) tuples."""
    if not rows:
        return
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=3000)
    parser.add_argument("--llm-model", default="gpt-5-mini")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true",
                        help="select and dictionary-label only, no LLM calls")
    args = parser.parse_args()

    load_dotenv()

    with db.connect() as conn:
        db.ensure_schema(conn)
        selection = select_sentences(conn, args.target)
        print(f"selected {len(selection)} sentences")

        with conn.cursor() as cur:
            upsert_labels(cur, [
                (sid, "dictionary", dictionary.classify(text), None)
                for sid, text in selection
            ])
        conn.commit()
        print("dictionary labels written")

        if args.dry_run:
            return

        # LLM labelling is network-bound, so requests are issued in
        # parallel and written to the database in batches.
        pending, failed = [], 0
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(llm_label.label_sentence, text, args.llm_model, CACHE_DIR): sid
                for sid, text in selection
            }
            for future in as_completed(futures):
                sid = futures[future]
                try:
                    label = future.result()
                except Exception as exc:
                    print(f"  sentence {sid} failed: {str(exc)[:100]}")
                    failed += 1
                    continue
                if label is None:
                    failed += 1
                    continue
                pending.append((sid, "llm", label["stance"], label["topic"]))
                done += 1
                if len(pending) >= 500:
                    with conn.cursor() as cur:
                        upsert_labels(cur, pending)
                    conn.commit()
                    pending = []
                    print(f"  {done} LLM labels...")
        with conn.cursor() as cur:
            upsert_labels(cur, pending)
        conn.commit()
        print(f"llm labels written: {done} ({failed} failed)")

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*),
                       count(*) FILTER (WHERE d.stance = l.stance)
                FROM labels d JOIN labels l ON d.sentence_id = l.sentence_id
                WHERE d.source = 'dictionary' AND l.source = 'llm'
                """
            )
            total, agree = cur.fetchone()
        if total:
            print(f"dictionary/llm stance agreement: {agree}/{total} ({agree/total:.1%})")


if __name__ == "__main__":
    main()
