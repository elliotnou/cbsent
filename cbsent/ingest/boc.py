"""Bank of Canada ingestion: fixed announcement date (FAD) press releases.

Rate decisions live at a stable URL pattern
(/YYYY/MM/fad-press-release-YYYY-MM-DD/), discovered by walking the press
release listing pages backwards. Announcements are stamped 10:00 a.m. ET
before 2024-01-24 and 9:45 a.m. ET from that date on.
"""

import datetime
import re
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup

from cbsent.ingest import fetch
from cbsent.ingest.times import boc_release_ts

LISTING_URL = "https://www.bankofcanada.ca/press/press-releases/page/{page}/"

_FAD_RE = re.compile(
    r"https://www\.bankofcanada\.ca/\d{4}/\d{2}/fad-press-release-(\d{4}-\d{2}-\d{2})/"
)

MAX_PAGES = 80


@dataclass
class BocRelease:
    url: str
    release_date: datetime.date


def list_releases(cache_dir: str, earliest: datetime.date) -> List[BocRelease]:
    """Walk the press release listing until we are past the earliest date."""
    seen = {}
    for page in range(1, MAX_PAGES + 1):
        try:
            html = fetch.get(LISTING_URL.format(page=page), cache_dir)
        except Exception:
            break
        for m in re.finditer(_FAD_RE, html):
            seen[m.group(0)] = datetime.date.fromisoformat(m.group(1))
        # The listing is reverse-chronological and mixes all press release
        # types, so a page may hold no FAD links; use every dated article
        # URL on the page to decide when we have walked past the window.
        page_dates = [
            datetime.date(int(y), int(mo), 1)
            for y, mo in re.findall(r"bankofcanada\.ca/(\d{4})/(\d{2})/", html)
        ]
        if page_dates and max(page_dates) < earliest.replace(day=1):
            break

    releases = [
        BocRelease(url, date)
        for url, date in seen.items()
        if date >= earliest
    ]
    releases.sort(key=lambda r: r.release_date)
    return releases


def fetch_document(release: BocRelease, cache_dir: str) -> Optional[dict]:
    html = fetch.get(release.url, cache_dir)
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    content_div = soup.find("div", class_="post-content")
    if content_div is None:
        return None
    paras = []
    for p in content_div.find_all("p"):
        text = p.get_text(" ", strip=True)
        # The closing "Information note" paragraph lists the next
        # announcement date; it carries no stance.
        if text:
            paras.append(text)
    content = "\n\n".join(paras)
    if len(content) < 200:
        return None

    meta = soup.find("meta", attrs={"name": "publication_date"})
    if meta and meta.get("content"):
        meta_date = datetime.date.fromisoformat(meta["content"][:10])
        if meta_date != release.release_date:
            print(f"warning: URL date {release.release_date} != meta date {meta_date} on {release.url}")

    return {
        "bank": "BOC",
        "doc_type": "rate_announcement",
        "url": release.url,
        "title": title,
        "published_at": boc_release_ts(release.release_date),
        "meeting_date": release.release_date,
        "content": content,
    }
