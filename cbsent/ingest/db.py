"""Database layer for the research corpus.

Two tables, `documents` and `sentences`. Every row in both carries
`published_at` (timestamptz); sentences denormalize it from their document
on purpose, so any query over sentences can filter on publication time
without a join and look-ahead bugs are structurally hard to write.
"""

import os
import datetime
from contextlib import contextmanager
from dataclasses import dataclass
from typing import List, Optional

import psycopg2
from dotenv import load_dotenv

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id           SERIAL PRIMARY KEY,
    bank         TEXT NOT NULL CHECK (bank IN ('FED', 'BOC')),
    doc_type     TEXT NOT NULL CHECK (doc_type IN ('statement', 'minutes', 'rate_announcement')),
    url          TEXT NOT NULL UNIQUE,
    title        TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    meeting_date DATE,
    content      TEXT NOT NULL,
    scraped_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sentences (
    id           SERIAL PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    seq          INTEGER NOT NULL,
    text         TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    UNIQUE (document_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_documents_published ON documents (published_at);
CREATE INDEX IF NOT EXISTS idx_sentences_published ON sentences (published_at);
CREATE INDEX IF NOT EXISTS idx_sentences_document ON sentences (document_id);
"""


@dataclass
class Document:
    bank: str
    doc_type: str
    url: str
    title: str
    published_at: datetime.datetime
    content: str
    meeting_date: Optional[datetime.date] = None


def _database_url() -> str:
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


@contextmanager
def connect():
    conn = psycopg2.connect(_database_url())
    try:
        yield conn
    finally:
        conn.close()


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()


def existing_urls(conn) -> set:
    with conn.cursor() as cur:
        cur.execute("SELECT url FROM documents")
        return {row[0] for row in cur.fetchall()}


def insert_document(conn, doc: Document, sentence_texts: List[str]) -> int:
    """Insert a document and its segmented sentences in one transaction."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (bank, doc_type, url, title, published_at, meeting_date, content)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """,
            (doc.bank, doc.doc_type, doc.url, doc.title,
             doc.published_at, doc.meeting_date, doc.content),
        )
        row = cur.fetchone()
        if row is None:
            conn.rollback()
            return 0
        doc_id = row[0]
        for seq, text in enumerate(sentence_texts):
            cur.execute(
                """
                INSERT INTO sentences (document_id, seq, text, published_at)
                VALUES (%s, %s, %s, %s)
                """,
                (doc_id, seq, text, doc.published_at),
            )
    conn.commit()
    return doc_id
