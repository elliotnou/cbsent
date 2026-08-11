"""Bank of Canada ingestion: fixed announcement date (FAD) press releases.

Rate decisions live at a date-determined URL
(/YYYY/MM/fad-press-release-YYYY-MM-DD/). The site's press release listing
paginates over all release types and stops surfacing older rate
announcements, so discovery enumerates candidate dates instead: fixed
announcement dates always fall midweek, so every Tuesday, Wednesday and
Thursday in the window is probed and the URLs that resolve are the real
announcements. Discovery is therefore deterministic and independent of site
navigation changes. The probe result for each date is cached.

Announcements are stamped 10:00 a.m. ET before 2024-01-24 and 9:45 a.m. ET
from that date on.
"""

import datetime
import json
import os
import time
from dataclasses import dataclass
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from cbsent.ingest import fetch
from cbsent.ingest.times import boc_release_ts

URL_TEMPLATE = "https://www.bankofcanada.ca/{d:%Y}/{d:%m}/fad-press-release-{d:%Y-%m-%d}/"

# Announcement weekdays to probe (Monday is 0).
CANDIDATE_WEEKDAYS = (1, 2, 3)

_INDEX_NAME = "boc_fad_index.json"


@dataclass
class BocRelease:
    url: str
    release_date: datetime.date


def _candidate_dates(earliest: datetime.date, latest: datetime.date):
    day = earliest
    while day <= latest:
        if day.weekday() in CANDIDATE_WEEKDAYS:
            yield day
        day += datetime.timedelta(days=1)


def list_releases(cache_dir: str, earliest: datetime.date,
                  latest: Optional[datetime.date] = None) -> List[BocRelease]:
    """Probe candidate announcement dates and return the ones that exist."""
    latest = latest or datetime.date.today()
    index_path = os.path.join(cache_dir, _INDEX_NAME)
    index = {}
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)

    session = requests.Session()
    session.headers["User-Agent"] = fetch.USER_AGENT

    probed = 0
    for day in _candidate_dates(earliest, latest):
        key = day.isoformat()
        if key in index:
            continue
        url = URL_TEMPLATE.format(d=day)
        try:
            resp = session.head(url, timeout=20, allow_redirects=False)
            index[key] = resp.status_code == 200
        except Exception:
            index[key] = False
        time.sleep(fetch.DELAY_SECONDS)
        probed += 1
        if probed % 25 == 0:
            print(f"  probed {probed} candidate dates...")

    os.makedirs(cache_dir, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=0, sort_keys=True)

    releases = [
        BocRelease(URL_TEMPLATE.format(d=datetime.date.fromisoformat(k)),
                   datetime.date.fromisoformat(k))
        for k, exists in index.items()
        if exists and earliest <= datetime.date.fromisoformat(k) <= latest
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
