"""USD/CAD price data for the event study.

Two sources, and every reported number records which one it used:

- Dukascopy tick history, fetched from their public datafeed. No account or
  key required. Files are .bi5 (LZMA-compressed fixed-width records), one
  per hour of the trading day, in UTC, with months numbered from zero.
  Records decode as (ms offset in hour, ask, bid, ask volume, bid volume)
  where prices are integer points of 1e-5 for USDCAD.
- The Bank of Canada Valet API daily USD/CAD rate (series FXUSDCAD,
  observed 16:30 ET) as the fallback when intraday is unavailable.
"""

import datetime
import lzma
import os
import struct
import time
from typing import List, Optional, Tuple

import requests

DUKAS_URL = (
    "https://datafeed.dukascopy.com/datafeed/{symbol}/{y:04d}/{m:02d}/{d:02d}/"
    "{h:02d}h_ticks.bi5"
)
POINT_VALUE = 1e-5
SYMBOL = "USDCAD"

MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 2.0
REQUEST_DELAY_SECONDS = 0.4

VALET_URL = (
    "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json"
    "?start_date={start}&end_date={end}"
)

# Dukascopy's datafeed rejects non-browser agents.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def _decode_bi5(raw: bytes, hour_start: datetime.datetime) -> List[Tuple[datetime.datetime, float]]:
    """Decode one hourly .bi5 file into (timestamp, mid price) pairs."""
    if not raw:
        return []
    data = lzma.LZMADecompressor().decompress(raw)
    out = []
    record = struct.Struct(">IIIff")
    for offset in range(0, len(data) - record.size + 1, record.size):
        ms, ask, bid, _, _ = record.unpack_from(data, offset)
        ts = hour_start + datetime.timedelta(milliseconds=ms)
        mid = (ask + bid) / 2.0 * POINT_VALUE
        out.append((ts, mid))
    return out


def fetch_intraday_hour(hour_start_utc: datetime.datetime, cache_dir: str,
                        session: Optional[requests.Session] = None):
    """Fetch one UTC hour of USD/CAD ticks, cached on disk."""
    os.makedirs(cache_dir, exist_ok=True)
    name = f"{SYMBOL}_{hour_start_utc:%Y%m%d_%H}.bi5"
    path = os.path.join(cache_dir, name)

    if os.path.exists(path):
        with open(path, "rb") as f:
            raw = f.read()
    else:
        url = DUKAS_URL.format(
            symbol=SYMBOL, y=hour_start_utc.year, m=hour_start_utc.month - 1,
            d=hour_start_utc.day, h=hour_start_utc.hour,
        )
        session = session or requests.Session()
        raw = None
        for attempt in range(MAX_RETRIES):
            resp = session.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 404:
                # Weekend and holiday hours simply do not exist.
                raw = b""
                break
            if resp.status_code == 200:
                raw = resp.content
                break
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
        if raw is None:
            raise RuntimeError(f"could not fetch {url} after {MAX_RETRIES} attempts")
        with open(path, "wb") as f:
            f.write(raw)
        time.sleep(REQUEST_DELAY_SECONDS)

    return _decode_bi5(raw, hour_start_utc)


def fetch_window(center_utc: datetime.datetime, minutes_before: int,
                 minutes_after: int, cache_dir: str):
    """Fetch ticks spanning a window around an event timestamp."""
    start = center_utc - datetime.timedelta(minutes=minutes_before)
    end = center_utc + datetime.timedelta(minutes=minutes_after)
    hour = start.replace(minute=0, second=0, microsecond=0)
    session = requests.Session()
    ticks = []
    while hour <= end:
        ticks.extend(fetch_intraday_hour(hour, cache_dir, session))
        hour += datetime.timedelta(hours=1)
    return [(ts, px) for ts, px in ticks if start <= ts <= end]


def fetch_daily_rates(cache_dir: str, start: datetime.date,
                      end: datetime.date) -> dict:
    """Daily USD/CAD rate from the Bank of Canada, as {date: rate}."""
    import json

    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"usdcad_daily_{start:%Y%m%d}_{end:%Y%m%d}.json")
    if not os.path.exists(path):
        url = VALET_URL.format(start=start.isoformat(), end=end.isoformat())
        resp = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        with open(path, "w", encoding="utf-8") as f:
            f.write(resp.text)

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    rates = {}
    for obs in payload.get("observations", []):
        value = obs.get("FXUSDCAD", {}).get("v")
        if value:
            rates[datetime.date.fromisoformat(obs["d"])] = float(value)
    return rates
