"""Scrape Hacker News submissions and comment trees via the Algolia API.

No auth required. Algolia search is free and rate-limit-tolerant.
Comment trees come from the Firebase API which returns one item per request --
we walk children iteratively.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .common import OUT_DIR, Row, load_seen, save_seen, write_rows_csv

QUERIES = ["Google Flow", "Veo 3 Flow", "Whisk Google"]
SINCE = int(datetime(2024, 12, 1, tzinfo=timezone.utc).timestamp())
ALGOLIA = "https://hn.algolia.com/api/v1/search"
ITEM_API = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
TIMEOUT = 20


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _get(url: str, **params) -> dict:
    r = requests.get(url, params=params or None, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _app_for(text: str) -> str:
    t = (text or "").lower()
    has_flow = "flow" in t
    has_whisk = "whisk" in t
    if has_flow and has_whisk:
        return "both"
    if has_whisk:
        return "whisk"
    return "flow"


def _iso(epoch: int | float | None) -> str | None:
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def walk_comments(item_id: int, root_id: str, rows: dict[str, Row], depth: int = 0) -> None:
    if depth > 20:
        return
    try:
        item = _get(ITEM_API.format(id=item_id))
    except Exception:
        return
    if not item or item.get("deleted") or item.get("dead"):
        # still walk kids even if this node is dead
        for kid in item.get("kids", []) if item else []:
            walk_comments(kid, root_id, rows, depth + 1)
        return
    if item.get("type") == "comment":
        body = item.get("text") or ""
        rid = f"hn_{item['id']}"
        rows[rid] = Row(
            source="hackernews",
            source_id=rid,
            app=_app_for(body),
            author=item.get("by"),
            date_iso=_iso(item.get("time")),
            country=None,
            rating=None,
            title=None,
            body=body,
            url=f"https://news.ycombinator.com/item?id={item['id']}",
            parent_id=root_id,
            score_or_upvotes=None,
            raw_json=json.dumps({"id": item["id"], "parent": item.get("parent")}),
        )
    for kid in item.get("kids", []) or []:
        walk_comments(kid, root_id, rows, depth + 1)


def main() -> Path:
    logger.info("Hacker News scrape")
    seen_ids = load_seen("hackernews")
    rows: dict[str, Row] = {}

    for q in QUERIES:
        logger.info(f"  search :: {q!r}")
        page = 0
        while True:
            try:
                resp = _get(ALGOLIA, query=q, tags="story", numericFilters=f"created_at_i>{SINCE}",
                            hitsPerPage=50, page=page)
            except Exception as e:
                logger.warning(f"   search err p{page}: {e}")
                break
            hits = resp.get("hits", [])
            if not hits:
                break
            for h in hits:
                hid = h.get("objectID")
                title = h.get("title") or ""
                body = h.get("story_text") or ""
                rid = f"hn_{hid}"
                rows[rid] = Row(
                    source="hackernews",
                    source_id=rid,
                    app=_app_for(f"{title} {body}"),
                    author=h.get("author"),
                    date_iso=h.get("created_at"),
                    country=None,
                    rating=None,
                    title=title,
                    body=body,
                    url=h.get("url") or f"https://news.ycombinator.com/item?id={hid}",
                    parent_id=None,
                    score_or_upvotes=h.get("points"),
                    raw_json=json.dumps({"id": hid, "num_comments": h.get("num_comments")}),
                )
                # walk comments via Firebase
                try:
                    item = _get(ITEM_API.format(id=hid))
                    for kid in (item or {}).get("kids", []) or []:
                        walk_comments(kid, rid, rows)
                except Exception as e:
                    logger.warning(f"   tree err for {hid}: {e}")
            logger.info(f"   p{page}: {len(hits)} stories (total rows {len(rows)})")
            page += 1
            if page >= (resp.get("nbPages") or 0):
                break

    out_rows = sorted(rows.values(), key=lambda r: r.date_iso or "", reverse=True)
    out_path = OUT_DIR / "hackernews.csv"
    write_rows_csv(out_rows, out_path)
    save_seen("hackernews", set(rows.keys()) | seen_ids)
    logger.success(f"hn rows: {len(out_rows)}")
    return out_path


if __name__ == "__main__":
    main()
