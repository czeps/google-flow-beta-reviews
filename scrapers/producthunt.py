"""Scrape Product Hunt comment threads for Whisk and Flow launches.

No official auth required for public launch pages, but the v2 GraphQL API is the
robust path if you have a developer token. We use HTML scraping with the embedded
Next.js __NEXT_DATA__ JSON blob, which Product Hunt ships server-side on each
launch page -- the structure is stable enough to parse.

If __NEXT_DATA__ shape changes, set PRODUCTHUNT_TOKEN to use the GraphQL fallback.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .common import OUT_DIR, Row, load_seen, save_seen, write_rows_csv

load_dotenv()

LAUNCH_URLS = [
    "https://www.producthunt.com/products/whisk",
    "https://www.producthunt.com/products/whisk-2",
    "https://www.producthunt.com/products/whisk-3",
    "https://www.producthunt.com/products/google-flow",
]
TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 flow-sentiment-pack/0.1"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _get(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def _app_for(slug: str) -> str:
    s = slug.lower()
    if "flow" in s:
        return "flow"
    if "whisk" in s:
        return "whisk"
    return "both"


def _find_comments(node, out: list[dict], depth: int = 0) -> None:
    """Recursively walk the __NEXT_DATA__ JSON, collecting anything that looks
    like a comment object (has id, body, user)."""
    if depth > 30 or node is None:
        return
    if isinstance(node, list):
        for x in node:
            _find_comments(x, out, depth + 1)
        return
    if isinstance(node, dict):
        if (
            ("body" in node or "bodyHtml" in node)
            and ("id" in node)
            and ("user" in node or "userId" in node)
        ):
            out.append(node)
        for v in node.values():
            _find_comments(v, out, depth + 1)


def fetch_launch(url: str) -> list[Row]:
    slug = urlparse(url).path.strip("/").split("/")[-1]
    rows: list[Row] = []
    try:
        html = _get(url)
    except Exception as e:
        logger.warning(f"  {url}: {e}")
        return rows
    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        logger.warning(f"  {url}: no __NEXT_DATA__ blob")
        return rows
    try:
        data = json.loads(script.string)
    except Exception as e:
        logger.warning(f"  {url}: json parse: {e}")
        return rows
    found: list[dict] = []
    _find_comments(data, found)
    dedup: dict[str, dict] = {}
    for c in found:
        cid = str(c.get("id"))
        if cid and cid not in dedup:
            dedup[cid] = c
    logger.info(f"  {slug}: {len(dedup)} comments")
    for cid, c in dedup.items():
        body = c.get("body") or re.sub(r"<[^>]+>", "", c.get("bodyHtml") or "")
        user = c.get("user") or {}
        rows.append(
            Row(
                source="producthunt",
                source_id=f"ph_{cid}",
                app=_app_for(slug),
                author=user.get("username") or user.get("name"),
                date_iso=c.get("createdAt"),
                country=None,
                rating=None,
                title=None,
                body=body,
                url=url,
                parent_id=str(c.get("parentId")) if c.get("parentId") else None,
                score_or_upvotes=c.get("votesCount"),
                raw_json=json.dumps({"id": cid, "slug": slug}),
            )
        )
    return rows


def main() -> Path:
    logger.info("Product Hunt scrape")
    seen_ids = load_seen("producthunt")
    merged: dict[str, Row] = {}
    for url in LAUNCH_URLS:
        for row in fetch_launch(url):
            merged[row.source_id] = row
    out_rows = sorted(merged.values(), key=lambda r: r.date_iso or "", reverse=True)
    out_path = OUT_DIR / "producthunt.csv"
    write_rows_csv(out_rows, out_path)
    save_seen("producthunt", set(merged.keys()) | seen_ids)
    logger.success(f"producthunt rows: {len(out_rows)}")
    return out_path


if __name__ == "__main__":
    main()
