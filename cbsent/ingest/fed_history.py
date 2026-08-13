"""Historical FOMC statements and minutes from the per-year archive pages.

The calendar page only covers recent years; /monetarypolicy/
fomchistoricalYYYY.htm holds each earlier year's statements and minutes
with the minutes' release dates.

Statement release times changed over the period: 2:15 p.m. ET was the
norm before 2011, press-conference meetings in 2011-2012 released at
12:30 p.m. while others stayed at 2:15, and from March 2013 every
statement moved to 2:00 p.m. (Federal Reserve, "Questions and Answers:
The Information Content of the Post-FOMC Meeting Press Conference",
FEDS Notes, 2021). Pre-2013 statements are stamped 2:15 p.m. without
distinguishing the 12:30 press-conference meetings; nothing downstream
reads intraday times for these years - the yield study uses daily
closes - and this caveat is recorded here rather than silently absorbed.
"""

import datetime
import re
from typing import List

from bs4 import BeautifulSoup

from cbsent.ingest import fetch
from cbsent.ingest.fed import FedRelease, _parse_date
from cbsent.ingest.times import ET

BASE = "https://www.federalreserve.gov"
HISTORY_URL = BASE + "/monetarypolicy/fomchistorical{year}.htm"

_STATEMENT_RE = re.compile(r"/newsevents/pressreleases/monetary(\d{8})a\.htm$")
_MINUTES_RE = re.compile(r"/monetarypolicy/fomcminutes(\d{8})\.htm$")
_RELEASED_RE = re.compile(r"Released\s+([A-Z][a-z]+ \d{1,2}, \d{4})")

MODERN_TIME_CUTOVER = datetime.date(2013, 3, 1)


def statement_release_ts(release_date: datetime.date) -> datetime.datetime:
    t = datetime.time(14, 0) if release_date >= MODERN_TIME_CUTOVER else datetime.time(14, 15)
    return datetime.datetime.combine(release_date, t, tzinfo=ET)


def list_releases(years, cache_dir: str) -> List[FedRelease]:
    releases: List[FedRelease] = []
    for year in years:
        html = fetch.get(HISTORY_URL.format(year=year), cache_dir)
        soup = BeautifulSoup(html, "lxml")

        for a in soup.find_all("a", href=_STATEMENT_RE):
            if a.get_text(strip=True) != "HTML":
                continue
            meeting = _parse_date(_STATEMENT_RE.search(a["href"]).group(1))
            releases.append(
                FedRelease("statement", BASE + a["href"], meeting, meeting)
            )

        for a in soup.find_all("a", href=_MINUTES_RE):
            if a.get_text(strip=True) != "HTML":
                continue
            meeting = _parse_date(_MINUTES_RE.search(a["href"]).group(1))
            context = a.parent.get_text(" ", strip=True)
            m = _RELEASED_RE.search(context)
            if not m:
                continue
            released = datetime.datetime.strptime(m.group(1), "%B %d, %Y").date()
            releases.append(
                FedRelease("minutes", BASE + a["href"], meeting, released)
            )

    releases.sort(key=lambda r: (r.release_date, r.doc_type))
    return releases
