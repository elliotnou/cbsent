
import os
import re
import io
import json
import psycopg2
import pandas as pd
import yfinance as yf
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fin-sent.vercel.app", "http://localhost:5173"], 
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
        # Get date range from your sentiment data
        conn = get_db_connection()
        query = "SELECT MIN(publish_date) as min_date, MAX(publish_date) as max_date FROM transcripts"
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty or df['min_date'].isna().any():
            # Fallback: get last 2 years of data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)
        else:
            start_date = df['min_date'].iloc[0]
            end_date = df['max_date'].iloc[0]
            # Add some buffer
            start_date = start_date - timedelta(days=30)
            end_date = end_date + timedelta(days=30)
        
        # Fetch USD/CAD data from Yahoo Finance
        ticker = yf.Ticker("USDCAD=X")
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            return []
        
        # Convert to DataFrame with date index
        fx_df = pd.DataFrame({
            'price': hist['Close']
        })
        fx_df.index = pd.to_datetime(fx_df.index).date
        
        # Create continuous date range and forward-fill
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        fx_df = fx_df.reindex(all_dates.date)
        fx_df = fx_df.ffill()  # Forward fill missing dates
        
        # Normalize the close price to 0-1 range for easier visualization
        min_price = fx_df['price'].min()
        max_price = fx_df['price'].max()
        fx_df['normalized'] = (fx_df['price'] - min_price) / (max_price - min_price)
        
        # Format for frontend
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
        

if __name__ == "__main__":
    import uvicorn
    print("Starting Dovetail Terminal API...")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)