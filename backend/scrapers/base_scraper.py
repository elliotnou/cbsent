import os
import re
import unicodedata
import psycopg2
from dotenv import load_dotenv

load_dotenv()

class CentralBankScraper:
    def __init__(self, bank_name):
        self.bank_name = bank_name

        db_url = os.getenv("DATABASE_URL")
        
        try:
            self.conn = psycopg2.connect(db_url)
            self.cursor = self.conn.cursor()
            print(f"Connected to Neon for {self.bank_name}")
        except Exception as e:
            print(f"Connection Error: {e}")
            raise

    def clean_text(self, text):
        if not text:
            return ""
        
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', ' ', text)
        text = text.replace('\xa0', ' ').replace('\u200b', ' ')
        text = re.sub(r'[-–—]{2,}', ' ', text)
        text = re.sub(r'[_*#]{2,}', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    # Saves scraped content to the Neon database
    def save_to_db(self, date, url, text):
        """
        Saves the scraped text to the 'transcripts' table.
        """
        try:
            cleaned = self.clean_text(text)
            
            if len(cleaned) < 100:
                print(f"Text too short, skipping.")
                return
            
            query = """
            INSERT INTO transcripts (bank_name, publish_date, content, url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING;
            """
            self.cursor.execute(query, (self.bank_name, date, cleaned, url))
            self.conn.commit()
            print(f"Saved {self.bank_name} transcript for {date}")
            
        except Exception as e:
            print(f"DB error: {e}")
            self.conn.rollback()

    def url_exists(self, url: str) -> bool:
        """Return True if the given URL already exists in the transcripts table."""
        try:
            q = "SELECT 1 FROM transcripts WHERE url = %s LIMIT 1;"
            self.cursor.execute(q, (url,))
            return self.cursor.fetchone() is not None
        except Exception as e:
            # On error, conservatively return False so scraping proceeds
            print(f"DB check error for url_exists({url}): {e}")
            return False

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
