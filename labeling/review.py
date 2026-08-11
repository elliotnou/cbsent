"""Human review queue for bootstrap labels.

Serves sentences in priority order:
  1. every sentence in the evaluation window (chronological holdout) that
     has any bootstrap label — the eval set must be fully human-verified,
  2. every dictionary/LLM stance disagreement outside the window,
  3. a stratified random sample of agreements (bank x year x stance).

Decisions are written as source='human' labels. Progress is resumable;
quit any time with q.

Usage:
    python labeling/review.py [--eval-start 2025-04-01] [--limit N]
"""

import argparse
import os
import random
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cbsent.ingest import db
from cbsent.llm_label import STANCES, TOPICS

SEED = 20250811

STANCE_KEYS = {"h": "hawkish", "d": "dovish", "n": "neutral"}
TOPIC_KEYS = {str(i + 1): t for i, t in enumerate(TOPICS)}


def build_queue(conn, eval_start: str, sample_per_cell: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.id, s.text, d.bank, extract(year from s.published_at)::int,
                   s.published_at >= %s AS in_eval,
                   max(l.stance) FILTER (WHERE l.source = 'dictionary'),
                   max(l.stance) FILTER (WHERE l.source = 'llm'),
                   max(l.topic)  FILTER (WHERE l.source = 'llm'),
                   bool_or(l.source = 'human')
            FROM sentences s
            JOIN documents d ON s.document_id = d.id
            JOIN labels l ON l.sentence_id = s.id
            GROUP BY s.id, s.text, d.bank, s.published_at
            """,
            (eval_start,),
        )
        rows = cur.fetchall()

    pending = [r for r in rows if not r[8]]
    eval_rows = [r for r in pending if r[4]]
    rest = [r for r in pending if not r[4]]
    disagree = [r for r in rest if r[5] is not None and r[6] is not None and r[5] != r[6]]
    agree = [r for r in rest if r not in disagree]

    rng = random.Random(SEED)
    cells = {}
    for r in agree:
        cells.setdefault((r[2], r[3], r[6]), []).append(r)
    sampled = []
    for cell in sorted(cells):
        pool = cells[cell]
        sampled.extend(rng.sample(pool, min(sample_per_cell, len(pool))))

    queue = eval_rows + disagree + sampled
    return queue, len(eval_rows), len(disagree), len(sampled)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-start", default="2025-04-01")
    parser.add_argument("--sample-per-cell", type=int, default=15)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    with db.connect() as conn:
        queue, n_eval, n_dis, n_sample = build_queue(
            conn, args.eval_start, args.sample_per_cell
        )
        if args.limit:
            queue = queue[: args.limit]

        print(f"queue: {len(queue)} sentences "
              f"({n_eval} eval window, {n_dis} disagreements, {n_sample} sampled)")
        print("keys: [h]awkish [d]ovish [n]eutral, then topic 1-5, "
              "[s]kip, [q]uit\n")

        done = 0
        for sid, text, bank, year, in_eval, dict_stance, llm_stance, llm_topic, _ in queue:
            print("-" * 72)
            tag = "EVAL" if in_eval else ("DISAGREE" if dict_stance != llm_stance else "SAMPLE")
            print(f"[{tag}] {bank} {year}   dictionary={dict_stance}  llm={llm_stance}/{llm_topic}")
            print(textwrap.fill(text, width=72))

            choice = input("stance> ").strip().lower()
            if choice == "q":
                break
            if choice == "s":
                continue
            if choice not in STANCE_KEYS:
                print("unrecognized, skipping")
                continue
            stance = STANCE_KEYS[choice]

            topic_menu = "  ".join(f"{k}={v}" for k, v in TOPIC_KEYS.items())
            t = input(f"topic ({topic_menu}, enter={llm_topic})> ").strip()
            topic = TOPIC_KEYS.get(t, llm_topic)
            if topic not in TOPICS:
                topic = None

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO labels (sentence_id, source, stance, topic)
                    VALUES (%s, 'human', %s, %s)
                    ON CONFLICT (sentence_id, source)
                    DO UPDATE SET stance = EXCLUDED.stance, topic = EXCLUDED.topic
                    """,
                    (sid, stance, topic),
                )
            conn.commit()
            done += 1

        print(f"\nreviewed {done} sentences this session")


if __name__ == "__main__":
    main()
