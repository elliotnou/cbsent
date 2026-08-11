"""Federal Reserve ingestion: FOMC statements and minutes.

Source is the official meeting calendar page, which lists every meeting of
the past several years with links to the statement and the minutes, plus
the exact date the minutes were released. Statements are stamped 2:00 p.m.
ET on the decision date; minutes 2:00 p.m. ET on their own release date,
never the meeting date.
"""

import datetime
import re
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup

from cbsent.ingest import fetch
from cbsent.ingest.times import fed_release_ts

BASE = "https://www.federalreserve.gov"
CALENDAR_URL = BASE + "/monetarypolicy/fomccalendars.htm"

_STATEMENT_RE = re.compile(r"/newsevents/pressreleases/monetary(\d{8})a\.htm$")
_MINUTES_RE = re.compile(r"/monetarypolicy/fomcminutes(\d{8})\.htm$")
_RELEASED_RE = re.compile(r"Released\s+([A-Z][a-z]+ \d{1,2}, \d{4})")


@dataclass
class FedRelease:
    doc_type: str
    url: str
    meeting_date: datetime.date
    release_date: datetime.date


def _parse_date(yyyymmdd: str) -> datetime.date:
    return datetime.datetime.strptime(yyyymmdd, "%Y%m%d").date()


def list_releases(cache_dir: str, earliest: datetime.date) -> List[FedRelease]:
    """Parse the FOMC calendar page into statement and minutes releases."""
    html = fetch.get(CALENDAR_URL, cache_dir)
    soup = BeautifulSoup(html, "lxml")
    releases: List[FedRelease] = []

    for a in soup.find_all("a", href=_STATEMENT_RE):
        meeting = _parse_date(_STATEMENT_RE.search(a["href"]).group(1))
        if meeting < earliest:
            continue
        releases.append(FedRelease("statement", BASE + a["href"], meeting, meeting))

    for a in soup.find_all("a", href=_MINUTES_RE):
        if a.get_text(strip=True) != "HTML":
            continue
        meeting = _parse_date(_MINUTES_RE.search(a["href"]).group(1))
        if meeting < earliest:
            continue
        # The release date appears as "(Released Month D, YYYY)" next to the link.
        context = a.parent.get_text(" ", strip=True)
        m = _RELEASED_RE.search(context)
        if not m:
            continue
        released = datetime.datetime.strptime(m.group(1), "%B %d, %Y").date()
        releases.append(FedRelease("minutes", BASE + a["href"], meeting, released))

    releases.sort(key=lambda r: (r.release_date, r.doc_type))
    return releases


def _article_paragraphs(soup: BeautifulSoup) -> List[str]:
    article = soup.find("div", id="article")
    if article is None:
        return []
    paras = []
    for p in article.find_all("p"):
        strong = p.find("strong")
        if strong and strong.get_text(strip=True) == "Attendance":
            continue
        text = p.get_text(" ", strip=True)
        if text:
            paras.append(text)
    return paras


def fetch_document(release: FedRelease, cache_dir: str) -> Optional[dict]:
    html = fetch.get(release.url, cache_dir)
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("h3", class_="title") or soup.find("h2") or soup.find("h3")
    title = title_tag.get_text(strip=True) if title_tag else ""

    paras = _article_paragraphs(soup)
    # Drop the release-time banner and share-footer noise if present.
    paras = [p for p in paras if not p.startswith("For release at")]
    content = "\n\n".join(paras)
    if len(content) < 300:
        return None

    # Statements carry their own release-time banner; check it agrees with
    # the 2:00 p.m. rule rather than silently trusting either source.
    banner = soup.find(string=re.compile(r"For release at"))
    if banner and "2:00 p.m." not in banner:
        print(f"warning: unexpected release time on {release.url}: {banner.strip()}")

    return {
        "bank": "FED",
        "doc_type": release.doc_type,
        "url": release.url,
        "title": title,
        "published_at": fed_release_ts(release.release_date),
        "meeting_date": release.meeting_date,
        "content": content,
    }
