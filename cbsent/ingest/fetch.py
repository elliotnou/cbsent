"""Polite HTTP fetching with an on-disk cache.

Every page fetched during ingestion is cached under data/raw/ so parsing
can be re-run (and audited) without re-hitting the source sites.
"""

import os
import re
import time

import requests

USER_AGENT = "cbsent-research/0.1 (contact: repo owner)"
DELAY_SECONDS = 1.0

_last_request = 0.0


def cache_path(cache_dir: str, url: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", url.split("://", 1)[-1]).strip("_")
    return os.path.join(cache_dir, slug[:200] + ".html")


def get(url: str, cache_dir: str, timeout: int = 30) -> str:
    """Fetch a URL, serving from cache when available."""
    global _last_request
    path = cache_path(cache_dir, url)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    wait = DELAY_SECONDS - (time.time() - _last_request)
    if wait > 0:
        time.sleep(wait)
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    _last_request = time.time()
    resp.raise_for_status()

    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(resp.text)
    return resp.text
