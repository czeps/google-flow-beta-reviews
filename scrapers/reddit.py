"""Scrape Reddit submissions and comments via PRAW.

Auth: requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT.
Create a "script" app at https://www.reddit.com/prefs/apps.

Known limit: 60 requests/minute on the free OAuth tier. PRAW handles throttling.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import praw
from dotenv import load_dotenv
from loguru import logger

from .common import OUT_DIR, Row, load_seen, save_seen, write_rows_csv

load_dotenv()

SUBREDDITS = ["Bard", "singularity", "GoogleAI", "aivideo", "StableDiffusion", "Whisk"]
QUERIES = [
    "Google Flow",
    "Flow Veo",
    "Veo 3",
    "Whisk Google Labs",
    "labs.google whisk",
]
SINCE_UTC = datetime(2024, 12, 1, tzinfo=timezone.utc).timestamp()


def _client() -> praw.Reddit:
    cid = os.getenv("REDDIT_CLIENT_ID")
    sec = os.getenv("REDDIT_CLIENT_SECRET")
    ua = os.getenv("REDDIT_USER_AGENT", "flow-sentiment-pack/0.1")
    if not cid or not sec:
        raise RuntimeError(
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set. "
            "Create a script app at https://www.reddit.com/prefs/apps"
        )
    return praw.Reddit(
        client_id=cid, client_secret=sec, user_agent=ua, ratelimit_seconds=60, check_for_async=False
    )


def _iso(epoch: float | int | None) -> str | None:
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _app_for(text: str) -> str:
    t = text.lower()
    has_flow = "flow" in t
    has_whisk = "whisk" in t
    if has_flow and has_whisk:
        return "both"
    if has_whisk:
        return "whisk"
    return "flow"


def submission_to_row(sub) -> Row:
    return Row(
        source="reddit",
        source_id=f"t3_{sub.id}",
        app=_app_for(f"{sub.title} {sub.selftext or ''}"),
        author=str(sub.author) if sub.author else None,
        date_iso=_iso(sub.created_utc),
        country=None,
        rating=None,
        title=sub.title,
        body=sub.selftext,
        url=f"https://reddit.com{sub.permalink}",
        parent_id=None,
        score_or_upvotes=sub.score,
        raw_json=json.dumps(
            {
                "id": sub.id,
                "subreddit": str(sub.subreddit),
                "num_comments": sub.num_comments,
                "permalink": sub.permalink,
            }
        ),
    )


def comment_to_row(c, parent_sub_id: str) -> Row:
    return Row(
        source="reddit",
        source_id=f"t1_{c.id}",
        app=_app_for(c.body or ""),
        author=str(c.author) if c.author else None,
        date_iso=_iso(c.created_utc),
        country=None,
        rating=None,
        title=None,
        body=c.body,
        url=f"https://reddit.com{c.permalink}" if hasattr(c, "permalink") else None,
        parent_id=parent_sub_id,
        score_or_upvotes=c.score,
        raw_json=json.dumps({"id": c.id, "parent_id": c.parent_id}),
    )


def main() -> Path:
    logger.info("Reddit scrape")
    seen_ids = load_seen("reddit")
    reddit = _client()
    rows: dict[str, Row] = {}

    for sr in SUBREDDITS:
        try:
            sub_iter = reddit.subreddit(sr)
            sub_iter.id  # touch to validate
        except Exception as e:
            logger.warning(f"  r/{sr} unavailable: {e}")
            continue
        for q in QUERIES:
            logger.info(f"  r/{sr} :: {q!r}")
            count = 0
            try:
                for submission in reddit.subreddit(sr).search(q, sort="new", time_filter="all", limit=200):
                    if submission.created_utc < SINCE_UTC:
                        continue
                    sub_row = submission_to_row(submission)
                    if sub_row.source_id in rows:
                        continue
                    rows[sub_row.source_id] = sub_row
                    count += 1
                    submission.comments.replace_more(limit=None)
                    for c in submission.comments.list():
                        cr = comment_to_row(c, sub_row.source_id)
                        if cr.source_id not in rows:
                            rows[cr.source_id] = cr
                            count += 1
            except Exception as e:
                logger.warning(f"   search failed: {e}")
            logger.info(f"   +{count} rows")

    out_rows = sorted(rows.values(), key=lambda r: r.date_iso or "", reverse=True)
    out_path = OUT_DIR / "reddit.csv"
    write_rows_csv(out_rows, out_path)
    save_seen("reddit", set(rows.keys()) | seen_ids)
    logger.success(f"reddit rows: {len(out_rows)}")
    return out_path


if __name__ == "__main__":
    main()
