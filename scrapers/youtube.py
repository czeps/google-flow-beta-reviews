"""Scrape YouTube video comments via Data API v3.

Auth: requires YOUTUBE_API_KEY (enable YouTube Data API v3 in Google Cloud Console).
Quota: 10,000 units/day. search.list costs 100; commentThreads.list costs 1.
With the defaults below (~3 queries * 50 results + ~150 comment-thread fetches),
one run costs about 450 units -- ~20 runs/day before the quota resets.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from .common import OUT_DIR, Row, load_seen, save_seen, write_rows_csv

load_dotenv()

QUERIES = ["Google Flow review", "Veo 3 review", "Whisk Google Labs review"]
PER_QUERY = 50


def _service():
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError(
            "YOUTUBE_API_KEY not set. Enable YouTube Data API v3 in Google Cloud Console "
            "and create an API key: https://console.cloud.google.com/apis/credentials"
        )
    return build("youtube", "v3", developerKey=key, cache_discovery=False)


def _app_for(text: str) -> str:
    t = text.lower()
    has_flow = "flow" in t
    has_whisk = "whisk" in t
    if has_flow and has_whisk:
        return "both"
    if has_whisk:
        return "whisk"
    return "flow"


def search_videos(yt, query: str, limit: int = PER_QUERY) -> list[str]:
    ids: list[str] = []
    token = None
    while len(ids) < limit:
        page_size = min(50, limit - len(ids))
        resp = yt.search().list(
            q=query, part="id", type="video", maxResults=page_size, pageToken=token
        ).execute()
        for item in resp.get("items", []):
            vid = item["id"].get("videoId")
            if vid:
                ids.append(vid)
        token = resp.get("nextPageToken")
        if not token:
            break
    return ids


def fetch_comments(yt, video_id: str) -> list[dict]:
    out: list[dict] = []
    token = None
    while True:
        try:
            resp = yt.commentThreads().list(
                part="snippet,replies", videoId=video_id, maxResults=100,
                textFormat="plainText", pageToken=token, order="time",
            ).execute()
        except HttpError as e:
            logger.warning(f"   comments disabled or error for {video_id}: {e.resp.status}")
            break
        for item in resp.get("items", []):
            out.append(item)
        token = resp.get("nextPageToken")
        if not token:
            break
    return out


def thread_to_rows(item: dict, video_id: str) -> list[Row]:
    rows: list[Row] = []
    top = item.get("snippet", {}).get("topLevelComment", {})
    top_id = top.get("id") or ""
    snip = top.get("snippet", {})
    body = snip.get("textDisplay", "")
    rows.append(
        Row(
            source="youtube",
            source_id=top_id,
            app=_app_for(body),
            author=snip.get("authorDisplayName"),
            date_iso=snip.get("publishedAt"),
            country=None,
            rating=None,
            title=None,
            body=body,
            url=f"https://www.youtube.com/watch?v={video_id}&lc={top_id}",
            parent_id=None,
            score_or_upvotes=snip.get("likeCount"),
            raw_json=json.dumps({"video_id": video_id, "kind": "top"}),
        )
    )
    for reply in (item.get("replies") or {}).get("comments", []) or []:
        rid = reply.get("id") or ""
        rsnip = reply.get("snippet", {})
        rbody = rsnip.get("textDisplay", "")
        rows.append(
            Row(
                source="youtube",
                source_id=rid,
                app=_app_for(rbody),
                author=rsnip.get("authorDisplayName"),
                date_iso=rsnip.get("publishedAt"),
                country=None,
                rating=None,
                title=None,
                body=rbody,
                url=f"https://www.youtube.com/watch?v={video_id}&lc={rid}",
                parent_id=top_id,
                score_or_upvotes=rsnip.get("likeCount"),
                raw_json=json.dumps({"video_id": video_id, "kind": "reply"}),
            )
        )
    return rows


def main() -> Path:
    logger.info("YouTube scrape")
    seen_ids = load_seen("youtube")
    yt = _service()
    rows: dict[str, Row] = {}

    for q in QUERIES:
        logger.info(f"  search :: {q!r}")
        try:
            vids = search_videos(yt, q, PER_QUERY)
        except HttpError as e:
            logger.error(f"   search failed: {e}")
            break
        logger.info(f"   {len(vids)} videos")
        for vid in vids:
            threads = fetch_comments(yt, vid)
            added = 0
            for t in threads:
                for r in thread_to_rows(t, vid):
                    if r.source_id and r.source_id not in rows:
                        rows[r.source_id] = r
                        added += 1
            logger.info(f"   {vid}: +{added} (total {len(rows)})")

    out_rows = sorted(rows.values(), key=lambda r: r.date_iso or "", reverse=True)
    out_path = OUT_DIR / "youtube.csv"
    write_rows_csv(out_rows, out_path)
    save_seen("youtube", set(rows.keys()) | seen_ids)
    logger.success(f"youtube rows: {len(out_rows)}")
    return out_path


if __name__ == "__main__":
    main()
