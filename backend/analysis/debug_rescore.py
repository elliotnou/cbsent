import os, sys, psycopg2, traceback
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_URL = os.getenv('DATABASE_URL')
print(f"DB_URL found: {bool(DB_URL)}", file=sys.stderr)

# Step 1: How many unscored?
conn = psycopg2.connect(DB_URL, connect_timeout=10)
cur = conn.cursor()
cur.execute("""
    SELECT t.id, LENGTH(t.content) as clen FROM transcripts t
    LEFT JOIN transcript_sentences s ON t.id = s.transcript_id
    WHERE s.id IS NULL
    ORDER BY t.id
    LIMIT 5
""")
rows = cur.fetchall()
print(f"Unscored sample (first 5): {rows}", file=sys.stderr)
cur.close()
conn.close()

if not rows:
    print("Nothing to process", file=sys.stderr)
    sys.exit(0)

# Step 2: Try to score just ONE transcript
tid, clen = rows[0]
print(f"\nProcessing transcript ID={tid} (content_len={clen})...", file=sys.stderr)

conn = psycopg2.connect(DB_URL, connect_timeout=10)
cur = conn.cursor()
cur.execute("SELECT content FROM transcripts WHERE id = %s", (tid,))
content = cur.fetchone()[0]
cur.close()
conn.close()
print(f"Content fetched: {len(content)} chars", file=sys.stderr)

# Import and run model
try:
    from sentiment_eng import ToneAnalyzer
    analyzer = ToneAnalyzer()
    result = analyzer.analyze_paragraph(content)
    print(f"Sentences produced: {len(result.sentences) if result else 0}", file=sys.stderr)
    
    if result and result.sentences:
        for s in result.sentences[:3]:
            print(f"  [{s.topic}] score={s.score:.3f}: {s.text[:80]}", file=sys.stderr)
        
        # Insert
        conn = psycopg2.connect(DB_URL, connect_timeout=10)
        cur = conn.cursor()
        data = [(tid, s.text, s.topic, s.score, s.weight, s.reasoning) for s in result.sentences]
        cur.executemany("""
            INSERT INTO transcript_sentences 
            (transcript_id, sentence_text, topic, stance_score, impact_weight, reasoning)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, data)
        conn.commit()
        print(f"Inserted {len(data)} sentences for ID={tid}", file=sys.stderr)
        cur.close()
        conn.close()
except Exception:
    traceback.print_exc(file=sys.stderr)
