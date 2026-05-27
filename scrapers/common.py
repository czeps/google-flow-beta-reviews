"""Shared schema, IO, and persistence helpers for all scrapers."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

from loguru import logger

OUT_DIR = Path(__file__).resolve().parent.parent / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

Source = Literal["play_store", "app_store", "reddit", "youtube", "hackernews", "producthunt"]
App = Literal["flow", "whisk", "both", "flow_music"]

CSV_FIELDS = [
    "source",
    "source_id",
    "app",
    "author",
    "date_iso",
    "country",
    "rating",
    "title",
    "body",
    "url",
    "parent_id",
    "score_or_upvotes",
    "raw_json",
]


@dataclass
class Row:
    """Unified schema row written to per-source CSVs and the combined output."""

    source: Source
    source_id: str
    app: App
    author: str | None
    date_iso: str | None
    country: str | None
    rating: int | float | None
    title: str | None
    body: str | None
    url: str | None
    parent_id: str | None
    score_or_upvotes: int | float | None
    raw_json: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_rows_csv(rows: Iterable[Row], path: Path) -> int:
    """Write rows to CSV, returning the count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow(r.to_dict())
            n += 1
    logger.info(f"wrote {n} rows -> {path.relative_to(OUT_DIR.parent)}")
    return n


def seen_path(source: Source) -> Path:
    return OUT_DIR / f".seen_{source}.json"


def load_seen(source: Source) -> set[str]:
    p = seen_path(source)
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text()))
    except Exception:
        logger.warning(f"could not read {p}; starting empty")
        return set()


def save_seen(source: Source, ids: Iterable[str]) -> None:
    p = seen_path(source)
    p.write_text(json.dumps(sorted(set(ids))))
