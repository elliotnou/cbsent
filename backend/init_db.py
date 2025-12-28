import os
import psycopg2

from dotenv import load_dotenv
load_dotenv()

def initialize_database():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor()

    commands = [
        "CREATE EXTENSION IF NOT EXISTS vector;",
        """
        CREATE TABLE IF NOT EXISTS transcripts (
            id SERIAL PRIMARY KEY,
            bank_name VARCHAR(10) NOT NULL,
            report_type VARCHAR(50),
            publish_date DATE,
            url TEXT UNIQUE NOT NULL,
            raw_text TEXT NOT NULL,
            embedding vector(768)  -- Holds the FinBERT AI data
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS policy_audits (
            id SERIAL PRIMARY KEY,
            transcript_id INTEGER REFERENCES transcripts(id),
            sentiment_score FLOAT,
            z_score FLOAT,
            is_regime_shift BOOLEAN DEFAULT FALSE
        );
        """
    ]

    try:
        for command in commands:
            cur.execute(command)
        conn.commit()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    initialize_database()
