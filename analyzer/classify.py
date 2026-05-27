"""Stage 2: classify every review against the finalised taxonomy.

For each review, returns the list of features it touches and a sentiment in
{-1, 0, +1} per feature. Appends to out/review_features.csv after every batch,
so a crash or Ctrl-C only loses the in-flight batch.

Uses Anthropic prompt caching on the taxonomy block (sent on every call),
so the second batch onward pays ~10% of the input-token cost for that prefix.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd
from anthropic import APIError
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .common import OUT_DIR, REVIEW_FEATURES_PATH, TAXONOMY_PATH, client, resolve_model

REVIEWS_CSV = OUT_DIR / "play_store.csv"
BATCH_SIZE = 10
OUTPUT_FIELDS = ["source_id", "feature_id", "sentiment"]

SYSTEM = """You classify user app reviews into a fixed feature taxonomy and assign sentiment per feature.

For each review, return ONLY the features it actually discusses (not every feature in the taxonomy). Sentiment refers to how the user feels about THAT FEATURE specifically -- it may differ from the review's overall star rating. A reviewer who gives 5 stars but complains the app is slow should get sentiment=-1 for the "performance" feature, even though their overall rating is positive.

Sentiment values:
+1 = positive (works well, user likes it, praise)
 0 = neutral (mention without clear positive/negative, mixed, or unclear)
-1 = negative (complaint, frustration, broken, missing)

If a review mentions no taxonomy feature, return an empty `features` array for it.

Reviews can be in any language. Classify the meaning, not the surface words. The taxonomy synonyms are hints, not an exhaustive trigger list.

Return STRICT JSON, no prose, no markdown fences:
{
  "reviews": [
    {"source_id": "<id from input>", "features": [{"id": "video_quality", "sentiment": -1}, ...]},
    ...
  ]
}
The output MUST contain one entry per input review (in the same order), even if features is empty."""


def load_taxonomy() -> tuple[dict, str]:
    if not TAXONOMY_PATH.exists():
        raise RuntimeError(f"{TAXONOMY_PATH} not found. Run: python -m analyzer.taxonomy")
    data = json.loads(TAXONOMY_PATH.read_text())
    features = data.get("features") or []
    if not features:
        raise RuntimeError("taxonomy has no features")
    # Compact prompt-friendly format.
    lines = ["TAXONOMY:"]
    for f in features:
        syns = ", ".join(f.get("synonyms") or [])
        lines.append(f"- {f['id']} ({f['name']}): {f.get('description','')} [synonyms: {syns}]")
    return data, "\n".join(lines)


def format_batch(rows: list[dict]) -> str:
    parts = []
    for r in rows:
        stars = r.get("rating") or "?"
        country = r.get("country") or "?"
        body = (r.get("body") or "").replace("\n", " ").strip()
        parts.append(f'[id={r["source_id"]} stars={stars} country={country}] {body}')
    return "\n".join(parts)


def load_existing_classified_ids() -> set[str]:
    if not REVIEW_FEATURES_PATH.exists():
        return set()
    df = pd.read_csv(REVIEW_FEATURES_PATH, dtype=str)
    return set(df["source_id"].unique())


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
def call_model(c, model: str, taxonomy_text: str, batch_text: str) -> dict:
    resp = c.messages.create(
        model=model,
        max_tokens=4096,
        system=[
            {"type": "text", "text": SYSTEM},
            {"type": "text", "text": taxonomy_text, "cache_control": {"type": "ephemeral"}},
        ],
        messages=[{"role": "user", "content": f"Classify these reviews:\n\n{batch_text}"}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        sys.stderr.write(text + "\n")
        raise RuntimeError(f"non-JSON: {e}")


def write_batch(rows: list[dict], result: dict) -> int:
    by_id = {r["source_id"]: r for r in result.get("reviews", [])}
    new_path = not REVIEW_FEATURES_PATH.exists()
    n = 0
    with REVIEW_FEATURES_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        if new_path:
            w.writeheader()
        for r in rows:
            classification = by_id.get(r["source_id"])
            features = (classification or {}).get("features") or []
            if not features:
                # Write a sentinel row so we know this review was processed.
                w.writerow({"source_id": r["source_id"], "feature_id": "_none", "sentiment": 0})
                n += 1
                continue
            for feat in features:
                w.writerow(
                    {
                        "source_id": r["source_id"],
                        "feature_id": feat.get("id", ""),
                        "sentiment": int(feat.get("sentiment", 0)),
                    }
                )
                n += 1
    return n


def main(argv: list[str] | None = None) -> Path:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="sonnet (default), haiku, or full model id")
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    ap.add_argument("--limit", type=int, default=0, help="if >0, only classify N reviews (testing)")
    ap.add_argument("--restart", action="store_true", help="ignore prior progress and start fresh")
    args = ap.parse_args(argv)

    if args.restart and REVIEW_FEATURES_PATH.exists():
        REVIEW_FEATURES_PATH.unlink()

    _, taxonomy_text = load_taxonomy()
    df = pd.read_csv(REVIEWS_CSV, dtype=str)
    df = df[df["body"].notna() & (df["body"].str.len() > 0)].reset_index(drop=True)
    done = load_existing_classified_ids()
    todo = df[~df["source_id"].isin(done)].reset_index(drop=True)
    if args.limit:
        todo = todo.head(args.limit)

    model = resolve_model(args.model)
    logger.info(f"model={model}  total={len(df)}  done={len(done)}  todo={len(todo)}  batch={args.batch_size}")
    if todo.empty:
        logger.success("nothing to do")
        return REVIEW_FEATURES_PATH

    c = client()
    total_rows = 0
    for i in range(0, len(todo), args.batch_size):
        batch_df = todo.iloc[i : i + args.batch_size]
        batch = batch_df.to_dict("records")
        batch_text = format_batch(batch)
        try:
            result = call_model(c, model, taxonomy_text, batch_text)
        except APIError as e:
            logger.error(f"  batch {i // args.batch_size + 1} failed permanently: {e}")
            continue
        n = write_batch(batch, result)
        total_rows += n
        logger.info(f"  batch {i // args.batch_size + 1}/{(len(todo) + args.batch_size - 1) // args.batch_size}: wrote {n} attribution rows (cum {total_rows})")

    logger.success(f"done. attribution rows appended: {total_rows} -> {REVIEW_FEATURES_PATH}")
    return REVIEW_FEATURES_PATH


if __name__ == "__main__":
    main()
