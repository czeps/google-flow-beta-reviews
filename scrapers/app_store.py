"""Scrape iOS App Store reviews via the public iTunes RSS feed.

Known limit: iTunes RSS caps at 500 reviews per country (10 pages * 50 reviews).
We fan out across countries and dedupe by review id.

Target: Google Flow Music (id 6760315723).
"""

from __future__ import annotations

import json
from pathlib import Path

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .common import OUT_DIR, Row, load_seen, save_seen, write_rows_csv

APP_ID = "6760315723"
COUNTRIES = ["us", "gb", "in", "de", "au", "ca", "ie"]
MAX_PAGE = 10
TIMEOUT = 20


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch(url: str) -> dict:
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "flow-sentiment-pack/0.1"})
    r.raise_for_status()
    return r.json()


def fetch_country(country: str) -> list[dict]:
    """Pull up to 10 pages * 50 reviews for one country."""
    seen: dict[str, dict] = {}
    for page in range(1, MAX_PAGE + 1):
        url = (
            f"https://itunes.apple.com/{country}/rss/customerreviews/"
            f"page={page}/id={APP_ID}/sortby=mostrecent/json"
        )
        try:
            data = _fetch(url)
        except requests.HTTPError as e:
            logger.info(f"   {country} p{page}: {e.response.status_code} (stop)")
            break
        except Exception as e:
            logger.warning(f"   {country} p{page}: {e}")
            break
        entries = data.get("feed", {}).get("entry") or []
        # Page 1 includes the app metadata as entry[0]; subsequent pages are pure reviews.
        if page == 1 and entries and "im:name" in entries[0]:
            entries = entries[1:]
        new = 0
        for e in entries:
            rid = e.get("id", {}).get("label")
            if rid and rid not in seen:
                seen[rid] = e
                new += 1
        logger.info(f"   {country} p{page}: got={len(entries)} new={new} total={len(seen)}")
        if not entries:
            break
    return list(seen.values())


def to_rows(raw: list[dict], country: str) -> list[Row]:
    rows: list[Row] = []
    for e in raw:
        rid = e.get("id", {}).get("label") or ""
        try:
            rating = int(e.get("im:rating", {}).get("label", "0")) or None
        except Exception:
            rating = None
        rows.append(
            Row(
                source="app_store",
                source_id=rid,
                app="flow_music",
                author=(e.get("author") or {}).get("name", {}).get("label"),
                date_iso=(e.get("updated") or {}).get("label"),
                country=country,
                rating=rating,
                title=(e.get("title") or {}).get("label"),
                body=(e.get("content") or {}).get("label"),
                url=(e.get("author") or {}).get("uri", {}).get("label"),
                parent_id=None,
                score_or_upvotes=None,
                raw_json=json.dumps(e, ensure_ascii=False),
            )
        )
    return rows


def main() -> Path:
    logger.info(f"App Store scrape: id={APP_ID}")
    seen_ids = load_seen("app_store")
    merged: dict[str, Row] = {}
    for country in COUNTRIES:
        raw = fetch_country(country)
        for row in to_rows(raw, country):
            merged[row.source_id] = row

    rows = sorted(merged.values(), key=lambda r: r.date_iso or "", reverse=True)
    out_path = OUT_DIR / "app_store.csv"
    write_rows_csv(rows, out_path)
    save_seen("app_store", set(merged.keys()) | seen_ids)
    logger.success(f"unique reviews: {len(rows)}")
    return out_path


if __name__ == "__main__":
    main()
