# Flow / Whisk Sentiment Scraping Pack

Pulls user reviews and discussion comments from six sources into a single CSV
for sentiment analysis of **Google Flow Beta** (Play Store
`com.google.android.apps.labs.whisk`), **Google Flow Music** (iOS
`6760315723`), and **Whisk** (sunsetted Google Labs web tool).

## Quick start

```bash
# 1. install deps (uv recommended)
export PATH="$HOME/Library/Python/3.13/bin:$PATH"
uv venv --python 3.13
uv pip install -r <(uv pip compile pyproject.toml)

# 2. copy + fill in keys for the auth-required sources (Reddit, YouTube)
cp .env.example .env
# edit .env

# 3. run everything (or a subset)
.venv/bin/python main.py
.venv/bin/python main.py play_store hackernews
.venv/bin/python main.py --skip reddit youtube
```

Each scraper is also standalone:

```bash
.venv/bin/python -m scrapers.play_store
.venv/bin/python -m scrapers.app_store
.venv/bin/python -m scrapers.reddit
.venv/bin/python -m scrapers.youtube
.venv/bin/python -m scrapers.hackernews
.venv/bin/python -m scrapers.producthunt
```

## Provisioning keys

| Source        | Auth?           | Where                                                                                                       |
| ------------- | --------------- | ----------------------------------------------------------------------------------------------------------- |
| Play Store    | none            | -                                                                                                           |
| App Store     | none            | -                                                                                                           |
| Hacker News   | none            | -                                                                                                           |
| Product Hunt  | none (HTML)     | Optional `PRODUCTHUNT_TOKEN` for GraphQL fallback (https://www.producthunt.com/v2/oauth/applications)        |
| Reddit        | required        | Create a **script** app at https://www.reddit.com/prefs/apps → set `REDDIT_CLIENT_ID`/`SECRET`/`USER_AGENT`  |
| YouTube       | required        | Enable **YouTube Data API v3** in https://console.cloud.google.com/apis/library/youtube.googleapis.com → API key → `YOUTUBE_API_KEY` |

## Unified schema

All scrapers emit rows with the same columns into `out/<source>.csv`, then
`main.py` concatenates them into `out/combined_reviews.csv` and
`combined_reviews.parquet`.

| column            | meaning                                                          |
| ----------------- | ---------------------------------------------------------------- |
| `source`          | `play_store` / `app_store` / `reddit` / `youtube` / `hackernews` / `producthunt` |
| `source_id`       | review/comment id within that source                             |
| `app`             | `flow` / `whisk` / `both` / `flow_music`                         |
| `author`          | username                                                         |
| `date_iso`        | ISO 8601 UTC                                                     |
| `country`         | 2-letter code (Play/App Store only)                              |
| `rating`          | 1–5 if applicable                                                |
| `title`           | review title or post title                                       |
| `body`            | review/comment text                                              |
| `url`             | deep link back to the source                                     |
| `parent_id`       | parent comment/submission id (replies)                           |
| `score_or_upvotes`| thumbs-up / upvotes / likes                                      |
| `raw_json`        | full original record for traceability                            |

Idempotency: each run writes `out/.seen_<source>.json` so re-runs union with
prior ids. Per-source CSVs are rewritten in full each run (last run wins inside
the source); the union dedup happens implicitly because each scraper dedupes by
its own id space.

## Expected volumes (rough)

| source       | rows                                | notes                                                  |
| ------------ | ----------------------------------- | ------------------------------------------------------ |
| play_store   | ~200 unique, ~7-day window          | Google caps the public reviews endpoint                |
| app_store    | 0–5 (tiny app)                      | iTunes RSS caps at 500/country                         |
| reddit       | low hundreds                        | depends on subreddit activity for the queries          |
| youtube      | low thousands (popular videos)      | quota-bound: 10k units/day                             |
| hackernews   | tens to low hundreds                | full comment trees walked recursively                  |
| producthunt  | tens                                | only comments on the four launch pages                 |

## Known limits

- **Play Store:** Google's public endpoint serves only the ~200 most recent
  text reviews per app, regardless of pagination tricks, country fan-out, or
  `num` size. The 960+ figure on the listing is the historical rating count;
  older reviews are not retrievable from any public endpoint. To get full
  history you need either the Google Play Developer API (publisher-only) or a
  paid archive service (AppFollow, Sensor Tower).
- **iTunes RSS:** hard cap of 500 reviews per country (10 pages × 50). Fan out
  across countries; expect heavy duplication.
- **Reddit:** 60 requests/minute on free OAuth. PRAW handles throttling.
- **YouTube:** 10,000 quota units/day. `search.list`=100, `commentThreads.list`=1.
  One full run is ~450 units.
- **Product Hunt:** HTML structure can drift. Falls back gracefully if the
  `__NEXT_DATA__` blob layout changes.
- **X/Twitter:** intentionally omitted — requires paid API access.
- **Flow iOS app:** TestFlight-only at time of writing, no public reviews exist.

## Feature analysis (Claude)

Turn the raw review corpus into a feature-level table with mention counts,
average star rating, and per-feature sentiment.

```bash
# add your Anthropic key to .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# stage 1: derive a 12-20 item feature taxonomy from a sample
.venv/bin/python -m analyzer.taxonomy
# inspect / hand-edit out/features_taxonomy.json before continuing

# stage 2: classify every review against the taxonomy (uses prompt caching)
.venv/bin/python -m analyzer.classify
# crash-safe: rerun after Ctrl-C to resume from out/review_features.csv

# stage 3: aggregate
.venv/bin/python -m analyzer.aggregate
# -> out/features.csv and out/features.json

# or run all three end to end
.venv/bin/python analyze.py
# (cheap mode: `python analyze.py --model haiku`)
```

Output schema (`features.csv`):
`feature_id, name, description, mention_count, avg_star_rating, positive_count,
negative_count, neutral_count, pct_positive, top_quotes`
