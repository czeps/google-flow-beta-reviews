"""Stage 1: derive a 12-20 item feature taxonomy from a sample of reviews.

Output: out/features_taxonomy.json

Pause after this stage so the user can review/edit the taxonomy before
classifying all 557 reviews against it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

from .common import OUT_DIR, TAXONOMY_PATH, client, resolve_model

REVIEWS_CSV = OUT_DIR / "play_store.csv"

SYSTEM = """You are analyzing user reviews of an AI video-generation Android app (Google Flow Beta, formerly Whisk).
Your job is to derive a clean, deduplicated taxonomy of the features and aspects users actually discuss.

Rules:
- 12 to 20 features. Fewer is better than more if they overlap.
- Features must be MUTUALLY EXCLUSIVE in spirit -- avoid two features that always co-occur.
- Cover both POSITIVE features (e.g., "video generation quality") and NEGATIVE concerns (e.g., "credit system / pricing", "content moderation strictness").
- Use snake_case ids that are short and stable.
- `name` is human-readable (3-5 words).
- `description` is one sentence explaining what counts as a mention.
- `synonyms` are 2-5 short phrases or keywords in any language that signal this feature.
- Reviews are in many languages -- the taxonomy is in English but synonyms can include other languages.

Return STRICT JSON, no prose, no markdown fences:
{
  "features": [
    {"id": "video_quality", "name": "Video generation quality", "description": "...", "synonyms": ["video", "render", "quality"]},
    ...
  ]
}"""


def build_sample(df: pd.DataFrame, n_random: int = 30, n_high_thumbs: int = 25, n_one_star: int = 25) -> pd.DataFrame:
    df = df.copy()
    df["rating_n"] = pd.to_numeric(df["rating"], errors="coerce")
    df["thumbs_n"] = pd.to_numeric(df["score_or_upvotes"], errors="coerce").fillna(0)
    df = df[df["body"].notna() & (df["body"].str.len() > 3)]

    high_thumbs = df.nlargest(n_high_thumbs, "thumbs_n")
    one_star = df[df["rating_n"] == 1].nlargest(n_one_star, "thumbs_n")
    used_ids = set(high_thumbs["source_id"]) | set(one_star["source_id"])
    remaining = df[~df["source_id"].isin(used_ids)]
    random_pick = remaining.sample(min(n_random, len(remaining)), random_state=42)
    return pd.concat([high_thumbs, one_star, random_pick], ignore_index=True)


def format_review_block(df: pd.DataFrame) -> str:
    lines: list[str] = []
    for _, r in df.iterrows():
        stars = "?" if pd.isna(r["rating_n"]) else f"{int(r['rating_n'])}"
        country = r.get("country") or "?"
        body = str(r["body"]).replace("\n", " ").strip()
        lines.append(f"[{stars}* {country}] {body}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> Path:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="sonnet (default), haiku, or full model id")
    ap.add_argument("--force", action="store_true", help="overwrite existing taxonomy")
    args = ap.parse_args(argv)

    if TAXONOMY_PATH.exists() and not args.force:
        logger.warning(f"{TAXONOMY_PATH} already exists; use --force to overwrite. Exiting.")
        return TAXONOMY_PATH

    df = pd.read_csv(REVIEWS_CSV, dtype=str)
    logger.info(f"loaded {len(df)} reviews")
    sample = build_sample(df)
    logger.info(f"sampled {len(sample)} reviews for taxonomy generation")

    block = format_review_block(sample)
    model = resolve_model(args.model)
    logger.info(f"calling {model}...")

    resp = client().messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Here are {len(sample)} sample reviews. Derive the feature taxonomy.\n\n{block}",
            }
        ],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()

    # Strip accidental fences just in case.
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        sys.stderr.write(text + "\n")
        raise RuntimeError(f"model returned non-JSON: {e}")

    features = data.get("features") or []
    if not features:
        raise RuntimeError(f"no features in response: {data}")

    TAXONOMY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    logger.success(f"wrote {len(features)} features -> {TAXONOMY_PATH}")
    logger.info("Review/edit it, then run: python -m analyzer.classify")
    return TAXONOMY_PATH


if __name__ == "__main__":
    main()
