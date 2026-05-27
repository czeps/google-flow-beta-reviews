"""Build the final deliverables from manual_classifications.jsonl.

Inputs:
  out/play_store.json              -- raw reviews (source of truth for ratings, dates, etc.)
  out/features_taxonomy.json       -- 20 feature definitions
  out/manual_classifications.jsonl -- per-review {en translation, lang, features+sentiment}

Outputs:
  out/play_store_translated.json   -- original + body_en + lang_detected per review
  out/review_features.csv          -- one row per (review, feature) attribution
  out/features.csv                 -- aggregated feature table (final deliverable)
  out/features.json                -- same, JSON
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

OUT = Path("out")
REVIEWS_JSON = OUT / "play_store.json"
TAX_JSON = OUT / "features_taxonomy.json"
MANUAL_JSONL = OUT / "manual_classifications.jsonl"

TRANSLATED_JSON = OUT / "play_store_translated.json"
REVIEW_FEATURES_CSV = OUT / "review_features.csv"
FEATURES_CSV = OUT / "features.csv"
FEATURES_JSON = OUT / "features.json"

MAX_QUOTES = 3
QUOTE_MAX_CHARS = 220


def load_manual() -> dict[str, dict]:
    d: dict[str, dict] = {}
    with MANUAL_JSONL.open() as f:
        for line in f:
            r = json.loads(line)
            d[r["id"]] = r
    return d


def build_translated(reviews: list[dict], manual: dict[str, dict]) -> None:
    out = []
    for r in reviews:
        m = manual.get(r["source_id"], {})
        row = dict(r)
        row["body_en"] = m.get("en", r.get("body"))
        row["lang_detected"] = m.get("lang", "en")
        out.append(row)
    TRANSLATED_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"wrote {len(out)} rows -> {TRANSLATED_JSON}")


def build_review_features(manual: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for rid, m in manual.items():
        feats = m.get("f") or []
        if not feats:
            rows.append({"source_id": rid, "feature_id": "_none", "sentiment": 0})
            continue
        for feat_id, sent in feats:
            rows.append({"source_id": rid, "feature_id": feat_id, "sentiment": int(sent)})
    df = pd.DataFrame(rows)
    df.to_csv(REVIEW_FEATURES_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"wrote {len(df)} attribution rows -> {REVIEW_FEATURES_CSV}")
    return df


def build_features_table(reviews: list[dict], manual: dict[str, dict], attr: pd.DataFrame, taxonomy: list[dict]) -> None:
    # Build a review-level dataframe with rating, thumbs, body_en
    rev_rows = []
    for r in reviews:
        m = manual.get(r["source_id"], {})
        rev_rows.append(
            {
                "source_id": r["source_id"],
                "rating": r.get("rating"),
                "thumbs": r.get("score_or_upvotes") or 0,
                "body": r.get("body") or "",
                "body_en": m.get("en") or r.get("body") or "",
                "country": r.get("country"),
                "lang_detected": m.get("lang", "en"),
            }
        )
    reviews_df = pd.DataFrame(rev_rows)
    reviews_df["rating"] = pd.to_numeric(reviews_df["rating"], errors="coerce")
    reviews_df["thumbs"] = pd.to_numeric(reviews_df["thumbs"], errors="coerce").fillna(0)

    # Drop the "_none" sentinel rows
    attr = attr[attr["feature_id"] != "_none"].copy()
    joined = attr.merge(reviews_df, on="source_id", how="left")

    tax_df = pd.DataFrame(taxonomy)[["id", "name", "description"]].rename(columns={"id": "feature_id"})

    agg_rows = []
    for fid, grp in joined.groupby("feature_id"):
        ratings = grp["rating"].dropna()
        unique = grp.drop_duplicates("source_id")
        n = len(unique)
        pos = int((grp["sentiment"] == 1).sum())
        neg = int((grp["sentiment"] == -1).sum())
        neu = int((grp["sentiment"] == 0).sum())

        # Top quotes: pick 3 reviews mentioning this feature with the most thumbs (or highest abs sentiment if tied)
        top = unique.sort_values(["thumbs"], ascending=False).head(MAX_QUOTES)
        quotes_en = " | ".join(top["body_en"].fillna("").astype(str).str.slice(0, QUOTE_MAX_CHARS))
        quotes_orig = " | ".join(top["body"].fillna("").astype(str).str.slice(0, QUOTE_MAX_CHARS))

        agg_rows.append(
            {
                "feature_id": fid,
                "mention_count": n,
                "avg_star_rating": round(float(ratings.mean()), 2) if len(ratings) else None,
                "positive_count": pos,
                "negative_count": neg,
                "neutral_count": neu,
                "pct_positive": round(pos / max(n, 1), 3),
                "pct_negative": round(neg / max(n, 1), 3),
                "top_quotes_en": quotes_en,
                "top_quotes_orig": quotes_orig,
            }
        )

    feats = pd.DataFrame(agg_rows).merge(tax_df, on="feature_id", how="left")
    feats = feats[
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
            "pct_negative",
            "top_quotes_en",
            "top_quotes_orig",
        ]
    ].sort_values("mention_count", ascending=False).reset_index(drop=True)

    feats.to_csv(FEATURES_CSV, index=False, quoting=csv.QUOTE_ALL)
    FEATURES_JSON.write_text(json.dumps(feats.to_dict(orient="records"), indent=2, ensure_ascii=False))
    print(f"wrote {len(feats)} feature rows -> {FEATURES_CSV} & {FEATURES_JSON}")


def main() -> None:
    reviews = json.loads(REVIEWS_JSON.read_text())
    taxonomy = json.loads(TAX_JSON.read_text())["features"]
    manual = load_manual()

    print(f"reviews: {len(reviews)}, taxonomy: {len(taxonomy)}, manual: {len(manual)}")

    build_translated(reviews, manual)
    attr = build_review_features(manual)
    build_features_table(reviews, manual, attr, taxonomy)


if __name__ == "__main__":
    main()
