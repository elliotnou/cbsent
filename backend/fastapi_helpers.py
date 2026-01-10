from fastapi import FastAPI
import psycopg2
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/divergence")
def get_divergence_data():
    conn = psycopg2.connect(...)
    cur = conn.cursor()
    
    query = """
        SELECT 
            t.publish_date,
            t.bank_name,
            ROUND(CAST(SUM(s.stance_score * s.impact_weight) / NULLIF(SUM(s.impact_weight), 0) AS NUMERIC), 3) as weighted_score
        FROM transcripts t
        JOIN transcript_sentences s ON t.id = s.transcript_id
        GROUP BY t.publish_date, t.bank_name
        ORDER BY t.publish_date ASC;
    """
    cur.execute(query)
    data = cur.fetchall()
    
    formatted = {}
    for date, bank, score in data:
        date_str = date.strftime("%Y-%m-%d")
        if date_str not in formatted:
            formatted[date_str] = {"date": date_str}
        formatted[date_str][bank.lower()] = float(score)
        
    return list(formatted.values())
