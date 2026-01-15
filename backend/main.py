
import os
import re
import io
import json
import psycopg2
import pandas as pd
import yfinance as yf
import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Suppress pandas SQLAlchemy warnings
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy.*')

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fin-sent.vercel.app", "http://localhost:5173", "http://localhost:5174", "https://finsent-530o.onrender.com"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
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

@app.get("/api/usdcad")
def get_usdcad():
    try:
        conn = get_db_connection()
        query = "SELECT MIN(publish_date) as min_date, MAX(publish_date) as max_date FROM transcripts"
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty or df['min_date'].isna().any():
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)
        else:
            start_date = df['min_date'].iloc[0]
            end_date = df['max_date'].iloc[0]
            start_date = start_date - timedelta(days=30)
            end_date = end_date + timedelta(days=30)

        ticker = yf.Ticker("USDCAD=X")
        hist = ticker.history(start=start_date, end=end_date)

        if hist.empty:
            return []

        fx_df = pd.DataFrame({'price': hist['Close']})
        fx_df.index = pd.to_datetime(fx_df.index).date

        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        fx_df = fx_df.reindex(all_dates.date).ffill()

        min_price = fx_df['price'].min()
        max_price = fx_df['price'].max()
        fx_df['normalized'] = (fx_df['price'] - min_price) / (max_price - min_price)

        result = []
        for date, row in fx_df.iterrows():
            if pd.notna(row['price']):
                result.append({
                    'date': pd.Timestamp(date).strftime('%Y-%m-%d'),
                    'price': round(float(row['price']), 4),
                    'normalized': round(float(row['normalized']), 4)
                })

        return result

    except Exception as e:
        print(f"USD/CAD fetch error: {e}")
        return []

@app.get("/api/transcripts")
def get_transcripts():
    try:
        conn = get_db_connection()

        query = """
            SELECT
                t.id,
                t.bank_name as bank,
                t.publish_date as date,
                t.content,
                t.url,
                AVG(ts.stance_score) as sentiment
            FROM transcripts t
            LEFT JOIN transcript_sentences ts ON t.id = ts.transcript_id
            GROUP BY t.id, t.bank_name, t.publish_date, t.content, t.url
            ORDER BY t.publish_date DESC
        """

        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            content = row['content'] if pd.notna(row['content']) else ''
            excerpt = content[:500] + '...' if content and len(content) > 500 else content

            title = ''
            if pd.notna(row['url']):
                url_parts = row['url'].split('/')
                title = url_parts[-1].replace('-', ' ').replace('_', ' ').title() if url_parts else ''
            if not title:
                title = f"{row['bank']} - {row['date'].strftime('%B %Y') if pd.notna(row['date']) else ''}"

            result.append({
                'id': int(row['id']),
                'bank': row['bank'],
                'date': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else '',
                'title': title,
                'excerpt': excerpt,
                'sentiment': round(float(row['sentiment']), 3) if pd.notna(row['sentiment']) else 0.0
            })

        return result

    except Exception as e:
        print(f"Transcripts fetch error: {e}")
        return []

@app.get("/api/transcripts/{transcript_id}/sentences")
def get_transcript_sentences(transcript_id: int):
    try:
        conn = get_db_connection()

        query = """
            SELECT
                ts.id,
                ts.sentence_text,
                ts.stance_score,
                ts.impact_weight,
                ts.topic,
                ts.reasoning
            FROM transcript_sentences ts
            WHERE ts.transcript_id = %s
            ORDER BY ts.id ASC
        """

        cursor = conn.cursor()
        cursor.execute(query, (transcript_id,))
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return []

        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            result.append({
                'id': row_dict['id'],
                'text': row_dict['sentence_text'] if row_dict['sentence_text'] else '',
                'score': round(float(row_dict['stance_score']), 3) if row_dict['stance_score'] is not None else 0.0,
                'impact': round(float(row_dict['impact_weight']), 3) if row_dict['impact_weight'] is not None else 0.0,
                'topic': row_dict['topic'] if row_dict['topic'] else '',
                'reasoning': row_dict['reasoning'] if row_dict['reasoning'] else ''
            })

        return result

    except Exception as e:
        print(f"Transcript sentences fetch error: {e}")
        return []


if __name__ == "__main__":
    import uvicorn
    print("Starting Dovetail Terminal API...")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)