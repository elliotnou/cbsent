"""Release-time rules for scheduled central bank publications.

Every document gets an exact publication timestamp so downstream code can
never accidentally look ahead. Times were verified against primary sources:

- FOMC statements are released at 2:00 p.m. ET, and minutes of regularly
  scheduled meetings three weeks after the decision, also at 2:00 p.m. ET
  (federalreserve.gov press release headers state "For release at 2:00 p.m.").
- Bank of Canada rate announcements were published at 10:00 a.m. ET until
  January 24, 2024, when they moved to 9:45 a.m. ET
  (bankofcanada.ca, "Bank of Canada announces changes to communications of
  interest rate decisions", December 2023).
"""

import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

BOC_TIME_CHANGE = datetime.date(2024, 1, 24)


def fed_release_ts(release_date: datetime.date) -> datetime.datetime:
    """FOMC statements and minutes: 2:00 p.m. ET on the release date."""
    return datetime.datetime.combine(release_date, datetime.time(14, 0), tzinfo=ET)


def boc_release_ts(release_date: datetime.date) -> datetime.datetime:
    """BoC rate announcements: 10:00 ET before 2024-01-24, 9:45 ET after."""
    t = datetime.time(9, 45) if release_date >= BOC_TIME_CHANGE else datetime.time(10, 0)
    return datetime.datetime.combine(release_date, t, tzinfo=ET)
