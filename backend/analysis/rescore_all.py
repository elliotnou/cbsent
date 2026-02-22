"""Batch re-score all unprocessed transcripts. Logs to rescore.log.
This version fetches ALL content first, then processes offline, then inserts."""
import os, sys, psycopg2, traceback
from dotenv import load_dotenv

LOGFILE = os.path.join(os.path.dirname(__file__), "rescore.log")

def log(msg):
    with open(LOGFILE, "a") as f:
        f.write(msg + "\n")
    print(msg)  # also print to stdout

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB_URL = os.getenv("DATABASE_URL")

# Step 1: Fetch ALL unscored transcript content in ONE query, then close connection
log("Fetching unscored transcripts...")
conn = psycopg2.connect(DB_URL, connect_timeout=15)
cur = conn.cursor()
cur.execute("""
    SELECT t.id, t.content FROM transcripts t
    LEFT JOIN transcript_sentences s ON t.id = s.transcript_id
    WHERE s.id IS NULL AND t.content IS NOT NULL AND LENGTH(t.content) > 10
    ORDER BY t.id
""")
transcripts = cur.fetchall()
cur.close()
conn.close()  # Close immediately — no more connection needed during inference
log(f"Fetched {len(transcripts)} transcripts into memory")

if not transcripts:
    log("Nothing to process")
    sys.exit(0)

# Step 2: Load model
log("Loading model...")
try:
    from sentiment_eng import ToneAnalyzer
    analyzer = ToneAnalyzer()
    log("Model loaded")
except Exception as e:
    log(f"FAILED to load model: {e}")
    sys.exit(1)

# Step 3: Process each transcript OFFLINE (no DB connection during inference)
all_results = []
for i, (tid, content) in enumerate(transcripts):
    try:
        result = analyzer.analyze_paragraph(content)
        if result and result.sentences:
            data = [(tid, s.text, s.topic, s.score, s.weight, s.reasoning) for s in result.sentences]
            all_results.append((tid, data))
            log(f"  [{i+1}/{len(transcripts)}] ID={tid}: {len(data)} sentences")
        else:
            log(f"  [{i+1}/{len(transcripts)}] ID={tid}: no sentences")
    except Exception as e:
        log(f"  [{i+1}/{len(transcripts)}] ID={tid}: ERROR - {e}")

log(f"\nInference complete. {len(all_results)} transcripts to insert")

# Step 4: Insert all results in one fresh connection
if all_results:
    conn = psycopg2.connect(DB_URL, connect_timeout=15)
    cur = conn.cursor()
    total = 0
    for tid, data in all_results:
        try:
            cur.executemany("""
                INSERT INTO transcript_sentences 
                (transcript_id, sentence_text, topic, stance_score, impact_weight, reasoning)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, data)
            conn.commit()
            total += len(data)
        except Exception as e:
            conn.rollback()
            log(f"  Insert error for ID={tid}: {e}")
    cur.close()
    conn.close()
    log(f"DONE: inserted {total} sentences")
else:
    log("DONE: nothing to insert")
