"""Stage 3: join attributions with reviews, produce the deliverable feature table.

Inputs:
  out/play_store.csv            -- review-level data (rating, body, thumbs)
  out/features_taxonomy.json    -- feature names + descriptions
  out/review_features.csv       -- per-review classifications from stage 2

Outputs:
  out/features.csv
  out/features.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from loguru import logger

from .common import (
    FEATURES_CSV,
    FEATURES_JSON,
    OUT_DIR,
    REVIEW_FEATURES_PATH,
    TAXONOMY_PATH,
)

REVIEWS_CSV = OUT_DIR / "play_store.csv"
MAX_QUOTES = 3
QUOTE_MAX_CHARS = 200


def main() -> Path:
    if not REVIEW_FEATURES_PATH.exists():
        raise RuntimeError(f"{REVIEW_FEATURES_PATH} not found. Run: python -m analyzer.classify")
    taxonomy = json.loads(TAXONOMY_PATH.read_text())["features"]
    tax_df = pd.DataFrame(taxonomy)[["id", "name", "description"]].rename(columns={"id": "feature_id"})

    reviews = pd.read_csv(REVIEWS_CSV, dtype=str)
    reviews["rating_n"] = pd.to_numeric(reviews["rating"], errors="coerce")
    reviews["thumbs_n"] = pd.to_numeric(reviews["score_or_upvotes"], errors="coerce").fillna(0)

    attr = pd.read_csv(REVIEW_FEATURES_PATH, dtype=str)
    attr["sentiment"] = pd.to_numeric(attr["sentiment"], errors="coerce").fillna(0).astype(int)
    attr = attr[attr["feature_id"] != "_none"]

    joined = attr.merge(reviews, on="source_id", how="left")

    rows = []
    for fid, grp in joined.groupby("feature_id"):
        ratings = grp["rating_n"].dropna()
        top_quotes = (
            grp.sort_values("thumbs_n", ascending=False)
            .drop_duplicates("source_id")
            .head(MAX_QUOTES)["body"]
            .fillna("")
            .str.slice(0, QUOTE_MAX_CHARS)
            .tolist()
        )
        n = grp["source_id"].nunique()
        pos = int((grp["sentiment"] == 1).sum())
        neg = int((grp["sentiment"] == -1).sum())
        neu = int((grp["sentiment"] == 0).sum())
        rows.append(
            {
                "feature_id": fid,
                "mention_count": n,
                "avg_star_rating": round(float(ratings.mean()), 2) if len(ratings) else None,
                "positive_count": pos,
                "negative_count": neg,
                "neutral_count": neu,
                "pct_positive": round(pos / max(n, 1), 3),
                "top_quotes": " | ".join(top_quotes),
            }
        )

    agg = pd.DataFrame(rows).merge(tax_df, on="feature_id", how="left")
    agg = agg[
        [
            "feature_id",
            "name",
            "description",
            "mention_count",
            "avg_star_rating",
            "positive_count",
            "negative_count",
            "neutral_count",
            "pct_positive",
            "top_quotes",
        ]
    ].sort_values("mention_count", ascending=False).reset_index(drop=True)

    agg.to_csv(FEATURES_CSV, index=False)
    FEATURES_JSON.write_text(json.dumps(agg.to_dict(orient="records"), indent=2, ensure_ascii=False))
    logger.success(f"wrote {len(agg)} features -> {FEATURES_CSV} & {FEATURES_JSON}")
    return FEATURES_CSV


if __name__ == "__main__":
    main()
