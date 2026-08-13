"""Bank of Canada speeches, from the press listing pages.

The listing at /press/speeches/ paginates ten items per page back through
the archive. Multimedia entries (press-conference videos) are skipped;
speech articles live at dated /YYYY/MM/slug/ URLs with the same
post-content structure as press releases.

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

LISTING_URL = "https://www.bankofcanada.ca/press/speeches/page/{page}/"

_ARTICLE_RE = re.compile(r"https://www\.bankofcanada\.ca/(\d{4})/(\d{2})/[a-z0-9-]+/$")

MAX_PAGES = 150


@dataclass
class BocSpeech:
    url: str
    title: str
    listed_date: Optional[datetime.date]


def list_speeches(cache_dir: str, earliest: datetime.date) -> List[BocSpeech]:
    seen = {}
    for page in range(1, MAX_PAGES + 1):
        try:
            html = fetch.get(LISTING_URL.format(page=page), cache_dir)
        except Exception:
            break
        soup = BeautifulSoup(html, "lxml")
        headings = soup.find_all("h3", class_="media-heading")
        if not headings:
            break
        page_dates = []
        for h3 in headings:
            a = h3.find("a")
            if not a or not a.get("href"):
                continue
            url = a["href"]
            if not _ARTICLE_RE.match(url):
                continue
            date_span = h3.find_previous("span", class_="media-date")
            listed = None
            if date_span:
                try:
                    listed = datetime.datetime.strptime(
                        date_span.get_text(strip=True), "%B %d, %Y"
                    ).date()
                except ValueError:
                    pass
            if listed:
                page_dates.append(listed)
            seen[url] = BocSpeech(url, a.get_text(strip=True), listed)
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
