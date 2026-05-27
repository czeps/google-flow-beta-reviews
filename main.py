"""Run every scraper, combine per-source CSVs into a single dataset.

Usage:
    python main.py                 # run everything
    python main.py play_store      # run only one source
    python main.py --skip reddit youtube
"""

from __future__ import annotations

import argparse
import importlib
import traceback
from pathlib import Path

import pandas as pd
from loguru import logger

from scrapers.common import CSV_FIELDS, OUT_DIR

SCRAPERS = ["play_store", "app_store", "reddit", "youtube", "hackernews", "producthunt"]


def run_one(name: str) -> tuple[str, int, str | None]:
    try:
        mod = importlib.import_module(f"scrapers.{name}")
        path = mod.main()
        df = pd.read_csv(path, dtype=str)
        return name, len(df), None
    except Exception as e:
        logger.error(f"{name} failed: {e}")
        traceback.print_exc()
        return name, 0, str(e)


def combine() -> tuple[Path, Path, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    for name in SCRAPERS:
        p = OUT_DIR / f"{name}.csv"
        if p.exists():
            df = pd.read_csv(p, dtype=str)
            frames.append(df)
    if not frames:
        raise RuntimeError("no per-source CSVs found; nothing to combine")
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.reindex(columns=CSV_FIELDS)
    csv_path = OUT_DIR / "combined_reviews.csv"
    pq_path = OUT_DIR / "combined_reviews.parquet"
    combined.to_csv(csv_path, index=False)
    combined.to_parquet(pq_path, index=False)
    return csv_path, pq_path, combined


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="*", help=f"subset of: {SCRAPERS}")
    ap.add_argument("--skip", nargs="*", default=[], help="sources to skip")
    args = ap.parse_args()

    targets = args.only if args.only else SCRAPERS
    targets = [t for t in targets if t not in args.skip]

    results: list[tuple[str, int, str | None]] = []
    for name in targets:
        logger.info(f"\n=== {name} ===")
        results.append(run_one(name))

    logger.info("\n=== combining ===")
    csv_path, pq_path, combined = combine()

    print("\n" + "=" * 60)
    print("PER-SOURCE COUNTS")
    print("=" * 60)
    for name, n, err in results:
        status = f"ERROR: {err}" if err else f"{n} rows"
        print(f"  {name:14s}  {status}")
    print(f"\nCombined: {len(combined)} rows")
    print(f"  CSV:     {csv_path}")
    print(f"  Parquet: {pq_path}")

    print("\nSAMPLE (5 rows, key columns):")
    sample_cols = ["source", "app", "date_iso", "country", "rating", "author", "body"]
    if len(combined) > 0:
        sample = combined.sample(min(5, len(combined)))[sample_cols].copy()
        sample["body"] = sample["body"].astype(str).str.slice(0, 80)
        print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
