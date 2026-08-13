"""Bank of Canada speeches, discovered through the paged RSS feed.

The /press/speeches/ listing page renders through a JavaScript module and
serves identical content for every page number, so it cannot be walked.
The WordPress feed for the speeches content type does paginate:
/feed/?content_type=speeches&paged=N returns ten items per page in
reverse-chronological order back through the archive, each with its URL,
title and publication date.

Speech pages carry a publication date but no clock time, so documents are
stamped 11:59 p.m. ET: for anything computed point-in-time, text with an
unknown release time must only become visible after the day is over.
"""

import datetime
import re
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup

from cbsent.ingest import fetch
from cbsent.ingest.times import ET

FEED_URL = ("https://www.bankofcanada.ca/feed/"
            "?content_type=speeches&post_type[0]=post&paged={page}")

_ARTICLE_RE = re.compile(r"https://www\.bankofcanada\.ca/\d{4}/\d{2}/[a-z0-9-]+/$")
# The feed is RSS 1.0 (RDF): items carry a dc:date rather than a pubDate.
_ITEM_RE = re.compile(
    r"<item rdf:about=\"[^\"]+\">.*?<title>(.*?)</title>"
    r".*?<link>(.*?)</link>.*?<dc:date>(.*?)</dc:date>",
    re.S,
)

MAX_PAGES = 200


@dataclass
class BocSpeech:
    url: str
    title: str
    listed_date: Optional[datetime.date]


def _unescape(text: str) -> str:
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.S)
    return (text.replace("&amp;", "&").replace("&#8217;", "'")
            .replace("&#8211;", "-").strip())


def list_speeches(cache_dir: str, earliest: datetime.date) -> List[BocSpeech]:
    seen = {}
    for page in range(1, MAX_PAGES + 1):
        try:
            xml = fetch.get(FEED_URL.format(page=page), cache_dir)
        except Exception:
            break
        items = _ITEM_RE.findall(xml)
        if not items:
            break
        page_dates = []
        for title, url, pub in items:
            url = url.strip()
            if not _ARTICLE_RE.match(url):
                continue
            try:
                listed = datetime.date.fromisoformat(pub.strip()[:10])
            except ValueError:
                listed = None
            if listed:
                page_dates.append(listed)
            seen[url] = BocSpeech(url, _unescape(title), listed)
        # Reverse-chronological: once a whole page is older, stop.
        if page_dates and max(page_dates) < earliest:
            break

    speeches = [s for s in seen.values()
                if s.listed_date is None or s.listed_date >= earliest]
    speeches.sort(key=lambda s: s.listed_date or datetime.date.min)
    return speeches


def fetch_document(speech: BocSpeech, cache_dir: str) -> Optional[dict]:
    try:
        html = fetch.get(speech.url, cache_dir)
    except Exception:
        return None
    soup = BeautifulSoup(html, "lxml")

    meta = soup.find("meta", attrs={"name": "publication_date"})
    if meta and meta.get("content"):
        day = datetime.date.fromisoformat(meta["content"][:10])
    elif speech.listed_date:
        day = speech.listed_date
    else:
        return None

    content_div = soup.find("div", class_="post-content")
    if content_div is None:
        return None
    paras = [p.get_text(" ", strip=True) for p in content_div.find_all("p")]
    content = "\n\n".join(p for p in paras if p)
    if len(content) < 500:
        return None

    return {
        "bank": "BOC",
        "doc_type": "speech",
        "url": speech.url,
        "title": speech.title,
        "published_at": datetime.datetime.combine(
            day, datetime.time(23, 59), tzinfo=ET
        ),
        "meeting_date": None,
        "content": content,
    }
