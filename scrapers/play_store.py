"""Scrape Google Play Store reviews for Google Flow Beta across countries.

Known limit: Google's public endpoint returns ~200 most-recent text reviews per
(country, sort) combination. We fan out across countries and sort orders, then
dedupe by reviewId to maximize unique reviews.
"""

from __future__ import annotations

import json
from pathlib import Path

from google_play_scraper import Sort, reviews
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .common import OUT_DIR, Row, load_seen, save_seen, write_rows_csv

APP_ID = "com.google.android.apps.labs.whisk"
# The Play Store endpoint caps at ~200 most-recent text reviews per
# (country, language) pair. Each language unlocks a separate pool; same-language
# country variants typically overlap heavily but occasionally surface extras.
# This matrix covers every Play Store-supported language with at least one
# country, plus multi-country fan-out for the high-volume languages
# (en/es/ar/pt/fr/zh). Countries without Play Store access (cn, ir, cu, kp, sy)
# are excluded.
LOCALES: list[tuple[str, str]] = [
    # English -- every major English-speaking market
    *[(c, "en") for c in ("us", "gb", "ca", "au", "nz", "ie", "in", "pk", "ph", "sg",
                          "my", "za", "ng", "ke", "gh", "tz", "ug", "zw", "jm", "tt")],
    # Spanish -- Spain + Latin America
    *[(c, "es") for c in ("es", "mx", "ar", "cl", "co", "pe", "ve", "uy", "ec", "bo",
                          "py", "cr", "gt", "pa", "do", "sv", "hn", "ni", "us")],
    # Portuguese -- pt-pt and pt-br pools
    *[(c, "pt") for c in ("pt", "br", "ao", "mz", "cv")],
    # French -- France, Belgium, Switzerland, Canada, Maghreb, francophone Africa
    *[(c, "fr") for c in ("fr", "be", "ch", "ca", "lu", "mc",
                          "ma", "dz", "tn", "sn", "ci", "cm", "ml", "bf", "mg")],
    # German -- DACH + Lux
    *[(c, "de") for c in ("de", "at", "ch", "lu", "li")],
    # Italian
    *[(c, "it") for c in ("it", "ch", "sm", "va")],
    # Dutch / Flemish
    *[(c, "nl") for c in ("nl", "be", "sr")],
    # Arabic -- whole MENA region
    *[(c, "ar") for c in ("sa", "ae", "eg", "ma", "dz", "tn", "kw", "qa", "bh",
                          "om", "jo", "lb", "iq", "ye", "ly", "sd", "ps")],
    # Chinese -- Traditional (Taiwan/HK) and Simplified (SG/MY diaspora)
    *[(c, "zh") for c in ("tw", "hk", "sg", "mo")],
    # Russian -- former USSR
    *[(c, "ru") for c in ("ru", "by", "kz", "kg", "uz", "tj", "am", "az", "md")],
    # Ukrainian
    [("ua", "uk")][0],
    # Turkish
    [("tr", "tr")][0],
    # Polish, Czech, Slovak, Hungarian, Romanian, Bulgarian
    [("pl", "pl")][0], [("cz", "cs")][0], [("sk", "sk")][0], [("hu", "hu")][0],
    *[(c, "ro") for c in ("ro", "md")],
    [("bg", "bg")][0],
    # Balkans
    [("hr", "hr")][0], [("rs", "sr")][0], [("ba", "bs")][0], [("si", "sl")][0],
    [("mk", "mk")][0], [("al", "sq")][0],
    # Baltics
    [("ee", "et")][0], [("lv", "lv")][0], [("lt", "lt")][0],
    # Nordics
    *[(c, "sv") for c in ("se", "fi")], [("no", "no")][0], [("dk", "da")][0],
    [("fi", "fi")][0], [("is", "is")][0],
    # Greek, Hebrew, Persian-Afghanistan, Pashto
    *[(c, "el") for c in ("gr", "cy")], [("il", "he")][0],
    # Southeast Asia
    [("id", "id")][0], [("th", "th")][0], [("vn", "vi")][0],
    [("my", "ms")][0], [("bn", "ms")][0],  # Brunei + Malaysia
    [("ph", "tl")][0],
    [("kh", "km")][0], [("la", "lo")][0], [("mm", "my")][0],
    # South Asia (India local languages + Bangladesh / Sri Lanka / Nepal)
    *[("in", lng) for lng in ("hi", "bn", "ta", "te", "ml", "kn", "gu", "mr", "pa", "ur")],
    [("pk", "ur")][0], [("bd", "bn")][0], [("lk", "si")][0], [("lk", "ta")][0],
    [("np", "ne")][0],
    # East Asia
    [("jp", "ja")][0], [("kr", "ko")][0],
    # Caucasus / Central Asia natives
    [("ge", "ka")][0], [("am", "hy")][0], [("az", "az")][0],
    [("kz", "kk")][0], [("uz", "uz")][0], [("kg", "ky")][0], [("mn", "mn")][0],
    # African languages
    *[(c, "sw") for c in ("ke", "tz", "ug")],
    [("et", "am")][0], [("za", "af")][0],
    # Spain regional
    [("es", "ca")][0], [("es", "eu")][0], [("es", "gl")][0],
    # Catch-all extras
    [("ir", "fa")][0],  # may 404 if Iran is blocked; we catch errors
]
# dedupe while preserving order
_seen: set[tuple[str, str]] = set()
LOCALES = [x for x in LOCALES if not (x in _seen or _seen.add(x))]
SORTS = [
    ("NEWEST", Sort.NEWEST),
    ("RATING", Sort.RATING),
    ("HELPFULNESS", Sort.MOST_RELEVANT),
]
PAGE_SIZE = 200


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_page(country: str, lang: str, sort_value: Sort, token: str | None) -> tuple[list[dict], str | None]:
    """Fetch a single page of reviews with retry on transient errors."""
    result, next_token = reviews(
        APP_ID,
        lang=lang,
        country=country,
        sort=sort_value,
        count=PAGE_SIZE,
        continuation_token=token,
    )
    return result, next_token


def fetch_combo(country: str, lang: str, sort_name: str, sort_value: Sort) -> list[dict]:
    """Paginate one (country, lang, sort) combo to exhaustion."""
    seen: dict[str, dict] = {}
    token = None
    page = 0
    while True:
        page += 1
        try:
            data, token = _fetch_page(country, lang, sort_value, token)
        except Exception as e:
            logger.error(f"   ! {country}/{lang}/{sort_name} p{page}: {e}")
            break
        new = sum(1 for r in data if r["reviewId"] not in seen)
        for r in data:
            seen[r["reviewId"]] = r
        logger.info(
            f"   {country}/{lang}/{sort_name} p{page}: got={len(data)} new={new} "
            f"total={len(seen)} token={'yes' if token else 'NO'}"
        )
        if not token or not data:
            break
        if page > 50:
            logger.warning("   page cap (50) hit, breaking")
            break
    return list(seen.values())


def to_rows(raw: list[dict], country: str) -> list[Row]:
    rows: list[Row] = []
    for r in raw:
        rows.append(
            Row(
                source="play_store",
                source_id=r["reviewId"],
                app="flow",
                author=r.get("userName"),
                date_iso=r["at"].isoformat() if r.get("at") else None,
                country=country,
                rating=r.get("score"),
                title=None,
                body=r.get("content"),
                url=f"https://play.google.com/store/apps/details?id={APP_ID}&reviewId={r['reviewId']}",
                parent_id=None,
                score_or_upvotes=r.get("thumbsUpCount"),
                raw_json=json.dumps(r, default=str, ensure_ascii=False),
            )
        )
    return rows


def main() -> Path:
    logger.info(f"Play Store scrape: {APP_ID}")
    seen_ids = load_seen("play_store")
    logger.info(f"  prior seen: {len(seen_ids)}")

    merged: dict[str, Row] = {}
    for country, lang in LOCALES:
        for sort_name, sort_value in SORTS:
            raw = fetch_combo(country, lang, sort_name, sort_value)
            for row in to_rows(raw, country):
                if row.source_id not in merged:
                    merged[row.source_id] = row

    rows = sorted(merged.values(), key=lambda r: r.date_iso or "", reverse=True)
    out_path = OUT_DIR / "play_store.csv"
    write_rows_csv(rows, out_path)

    save_seen("play_store", set(merged.keys()) | seen_ids)
    logger.success(f"unique reviews: {len(rows)}")
    return out_path


if __name__ == "__main__":
    main()
