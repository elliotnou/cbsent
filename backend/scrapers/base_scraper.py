import os
import re
import unicodedata
import psycopg2
from dotenv import load_dotenv

load_dotenv()

class CentralBankScraper:
    def __init__(self, bank_name):
        self.bank_name = bank_name
        self.conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        self.cursor = self.conn.cursor()

    def clean_text(self, text):
        if not text:
            return ""
        
        return text.strip()

    def save_to_db(self, date, url, text, report_type):
        try:
            cleaned = self.clean_text(text)
            
            if len(cleaned) < 100:
                print(f"Text too short ({len(cleaned)} chars), skipping: {url}")
                return
            
            query = """
            INSERT INTO transcripts (bank_name, publish_date, url, raw_text, report_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING;
            """
            self.cursor.execute(query, (self.bank_name, date, url, cleaned, report_type))
            self.conn.commit()
            print(f"Saved: {url[:60]}")
            
        except Exception as e:
            print(f"DB error: {e}")
            self.conn.rollback()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
