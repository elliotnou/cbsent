import os
import re
import io
import json
import psycopg2
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is missing from .env")
    return psycopg2.connect(db_url)

@app.get("/api/divergence") 
def get_divergence():
    try:
        conn = get_db_connection()

        query = """
            SELECT publish_date as date, bank_name, AVG(stance_score) as sentiment 
            FROM transcript_sentences 
            JOIN transcripts ON transcript_sentences.transcript_id = transcripts.id 
            GROUP BY 1, 2
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            return []

        df = df.pivot(index='date', columns='bank_name', values='sentiment')

        all_dates = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
        df = df.reindex(all_dates)

        df = df.ffill().fillna(0) 

        fed_col = 'Fed' if 'Fed' in df.columns else 'fed'
        boc_col = 'BoC' if 'BoC' in df.columns else 'boc'
        
        df['divergence'] = df[fed_col] - df[boc_col]

        df = df.reset_index().rename(columns={'index': 'date'})
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        df = df.rename(columns={fed_col: 'fed', boc_col: 'boc'})
        
        return df.to_dict(orient='records')
        
    except Exception as e:
        print(f"Server Error: {e}")
        return []
    
if __name__ == "__main__":
    import uvicorn
    print("Starting Dovetail Terminal API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)