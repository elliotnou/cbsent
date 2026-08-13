"""Federal Reserve speeches and testimony, from the official JSON feeds.

The feeds at /json/ne-speeches.json and /json/ne-testimony.json list every
speech since 2006 and testimony appearance with an exact Eastern-time
publication datetime, which becomes the document's published_at. Article
text is extracted the same way as statements and minutes.

These documents feed the unlabelled domain-adaptation corpus; they are
not part of the labelled stance dataset.
"""

import datetime
import json
import re
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup

from cbsent.ingest import fetch
from cbsent.ingest.times import ET

BASE = "https://www.federalreserve.gov"
FEEDS = {
    "speech": BASE + "/json/ne-speeches.json",
    "testimony": BASE + "/json/ne-testimony.json",
}

_DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}( \d{1,2}:\d{2}:\d{2} [AP]M)?$")


@dataclass
class FedFeedItem:
    doc_type: str
    url: str
    title: str
    published_at: datetime.datetime


def _parse_feed_datetime(raw: str) -> Optional[datetime.datetime]:
    raw = raw.strip()
    if not _DATE_RE.match(raw):
        return None
    if " " in raw:
        dt = datetime.datetime.strptime(raw, "%m/%d/%Y %I:%M:%S %p")
    else:
        # A handful of old entries carry no clock time; noon ET is used as
        # a neutral placeholder for corpus documents.
        dt = datetime.datetime.strptime(raw, "%m/%d/%Y").replace(hour=12)
    return dt.replace(tzinfo=ET)


def list_items(doc_type: str, cache_dir: str,
               earliest: datetime.date) -> List[FedFeedItem]:
    raw = fetch.get(FEEDS[doc_type], cache_dir)
    entries = json.loads(raw.encode().decode("utf-8-sig")
                         if raw.startswith("﻿") else raw)
    items = []
    for entry in entries:
        link = entry.get("l", "")
        title = (entry.get("t") or "").strip()
        published = _parse_feed_datetime(entry.get("d", "") or "")
        if not link.endswith(".htm") or not title or published is None:
            continue
        if published.date() < earliest:
            continue
        items.append(FedFeedItem(doc_type, BASE + link, title, published))
    items.sort(key=lambda x: x.published_at)
    return items


def fetch_document(item: FedFeedItem, cache_dir: str) -> Optional[dict]:
    try:
        html = fetch.get(item.url, cache_dir)
    except Exception:
        return None
    soup = BeautifulSoup(html, "lxml")
    article = soup.find("div", id="article")
    if article is None:
        return None
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)
        # Footnote and reference blocks add citation noise, not prose.
        if text and not text.startswith(("Return to text", "1.", "References")):
            paras.append(text)
    content = "\n\n".join(paras)
    if len(content) < 500:
        return None
    return {
        "bank": "FED",
        "doc_type": item.doc_type,
        "url": item.url,
        "title": item.title,
        "published_at": item.published_at,
        "meeting_date": None,
        "content": content,
    }
