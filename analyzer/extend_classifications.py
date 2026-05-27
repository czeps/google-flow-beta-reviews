"""Extend manual_classifications.jsonl with use-case / behavior tags.

For each review, keyword-match against the English translation to detect
use-case / behavior themes and append them to the existing `f` array.
Existing feature attributions are preserved verbatim.

Reads:  out/manual_classifications.jsonl, out/play_store_translated.json
Writes: out/manual_classifications.jsonl (in place; backed up to .bak)
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

OUT = Path("out")
JSONL = OUT / "manual_classifications.jsonl"
TRANSLATED = OUT / "play_store_translated.json"
BACKUP = JSONL.with_suffix(".jsonl.bak")


def has_any(text: str, patterns: list[str]) -> bool:
    return any(p in text for p in patterns)


def has_word(text: str, words: list[str]) -> bool:
    # word-boundary match for short words to avoid false positives
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def detect(en: str, rating: int | None) -> list[tuple[str, int]]:
    """Return list of (tag, sentiment) to ADD to this review's f array."""
    t = en.lower()
    tags: list[tuple[str, int]] = []

    # --- finally_mobile_companion (+1) ---
    if has_any(
        t,
        [
            "finally an app",
            "finally a app",
            "finally a mobile",
            "finally the app",
            "finally the application",
            "finally flow",
            "finally have flow",
            "been waiting for this",
            "been waiting for the app",
            "i was waiting for",
            "i have been waiting",
            "now i can use",
            "now i can quickly",
            "now via android",
            "now its mobile",
            "now it has come",
            "pocket-sized",
            "now on phone",
            "now on smartphone",
            "as an app",
            "via android",
            "release the app",
            "released the app",
            "finally they made",
            "now it's an app",
            "now there's an app",
            "happy to have flow as an app",
            "having the app",
            "now it has come out",
            "have the app",
            "I've been waiting for this",
        ],
    ):
        tags.append(("finally_mobile_companion", 1))

    # --- nostalgia_for_old_version (-1) ---
    if has_any(
        t,
        [
            "bring back",
            "old version was",
            "previous version was",
            "before the update",
            "after the update",
            "after this update",
            "after the latest update",
            "the latest update",
            "the recent update",
            "this new update",
            "after the recent updates",
            "since the update",
            "yesterday's version was better",
            "the old design",
            "the old interface",
            "the old way",
            "old design was",
            "bad update, old update is best",
            "previous version was best",
            "the old one could",
            "the website was better",
            "before, the tool was great",
            "before, it was simple",
            "used to be simple",
            "used to be great",
            "used to be good",
            "ruined the",
        ],
    ):
        tags.append(("nostalgia_for_old_version", -1))

    # --- for_content_creators ---
    if has_any(
        t,
        [
            "content creator",
            "for content creators",
            "content creators",
            "for youtube",
            "youtube content",
            "youtube video",
            "youtube videos",
            "content makers",
            "creators easy",
            "for creators",
            "ai content creating",
            "tiktok",
            "instagram",
            "shorts",
            "reels",
            "social media",
            "ugc",
            "for ai creators",
            "for indian young film",
            "if you're a creator",
        ],
    ):
        # sentiment: if praising → +1, complaining → -1, otherwise neutral
        if has_any(t, ["best for content creators", "easy for", "easier", "best app", "amazing", "wonderful", "love this"]):
            sent = 1
        elif has_any(t, ["my youtube content is stuck", "useless for", "ruined"]):
            sent = -1
        else:
            sent = 0
        tags.append(("for_content_creators", sent))

    # --- for_personal_photos ---
    if has_any(
        t,
        [
            "animate photos",
            "animate my photo",
            "animating personal",
            "my photos to life",
            "my baseball",
            "my friend's birthday",
            "my friend's photo",
            "my family",
            "to animate photos",
            "good to animate",
            "edit my friend",
            "photos to life",
            "baby photos",
            "my baby",
        ],
    ):
        tags.append(("for_personal_photos", 1))

    # --- beta_patience (neutral) ---
    if has_any(
        t,
        [
            "still in beta",
            "still beta",
            "still a beta",
            "it's still beta",
            "since it's still beta",
            "it is still",
            "still in early",
            "since it is still beta",
            "for a beta version",
            "good for a beta",
            "for an early build",
            "for a first version",
            "for now i'll",
            "for now, i",
            "3 stars for now",
            "four stars for now",
            "three stars for now",
            "4 stars for now",
            "stars for now",
            "small bugs",
            "minor bugs",
            "few minor bugs",
            "small errors",
            "considering the small errors",
            "i'll give four stars",
            "hopefully the next update fixes",
            "hopefully it gets better",
            "hope it improves",
            "hope it gets better",
            "i'm waiting for more improvements",
            "future updates could make",
            "i'm looking forward to more",
            "needs refinement",
            "needs more work",
            "needs improvement",
            "needs to fix",
            "expecting improvements",
            "still in development",
        ],
    ):
        tags.append(("beta_patience", 0))

    # --- competes_with_other_ai (neutral comparison) ---
    competitor_terms = [
        "chatgpt",
        "gpt",
        "sora",
        "midjourney",
        "grok",
        "runway",
        "pika",
        "stable diffusion",
        "dreamina",
        "seedance",
        "claude",
        "use gemini",
        "than gemini",
        "than chatgpt",
        "better than gpt",
        "worse than grok",
        "than other ai apps",
        "than many apps",
        "other ai apps",
        "other apps",
        "other ai",
        "than other apps",
    ]
    if has_any(t, competitor_terms):
        # Sentiment based on direction of comparison
        if has_any(t, ["better than gpt", "better than chatgpt", "better than gemini", "world-class", "stronger than"]):
            sent = 1
        elif has_any(t, ["worse than grok", "use gemini or chatgpt", "i prefer to download", "use chatgpt", "way better than this", "much better than"]):
            sent = -1
        else:
            sent = 0
        tags.append(("competes_with_other_ai", sent))

    # --- wasted_credits_on_failures (-1) ---
    if has_any(
        t,
        [
            "wasted credits",
            "wasted my credits",
            "wasted credit",
            "credits wasted",
            "lost credits",
            "lose credits",
            "lost my credit",
            "lost my 400",
            "consumes credits",
            "consuming credits",
            "deducts credits",
            "still deducts",
            "still takes credit",
            "still consuming",
            "without giving result",
            "credits and not generating",
            "wasted credits for free",
            "deduct credits from",
            "uses up the quota",
            "ran out of uses",
            "doesn't return credits when",
            "credits even with wrong",
            "burn through your credits",
        ],
    ):
        tags.append(("wasted_credits_on_failures", -1))

    # --- wants_free_tier (neutral pricing request) ---
    if has_any(
        t,
        [
            "please make it free",
            "make it free",
            "should be free",
            "free for poor",
            "for the poor",
            "for poor public",
            "without paying",
            "without need to pay",
            "without points or credits",
            "without payment",
            "completely limitless without",
            "give a free",
            "keep this free",
            "keep this app free",
            "keep it free",
            "more credits",
            "free credits",
            "more free",
            "should be unlimited",
            "if only the image generations were completely limitless",
            "free trial",
            "give me a free account",
            "give 50 credits",
            "credit be 200",
            "make the credit be",
            "remains free long-term",
        ],
    ):
        tags.append(("wants_free_tier", 0))

    # --- recommends_to_others (+1) ---
    if has_any(
        t,
        [
            "i recommend",
            "i advise everyone to download",
            "you must try",
            "must try",
            "you have to try",
            "highly recommend",
            "deserves downloading",
            "super recommend",
            "recommend it",
            "i recommend it",
            "you need to try this",
        ],
    ):
        tags.append(("recommends_to_others", 1))

    # --- not_recommended (-1) ---
    if has_any(
        t,
        [
            "i don't recommend",
            "don't recommend",
            "don't download",
            "i advise you don't",
            "i don't advise",
            "don't waste your time",
            "don't waste",
            "you should not download",
            "stay away",
            "no one should download",
            "do not download",
            "i advise you,",
            "take it down",
        ],
    ):
        tags.append(("not_recommended", -1))

    # --- voice_audio_quality (-1 typically) ---
    if has_any(
        t,
        [
            "voiceover",
            "voice over",
            "robotic voice",
            "ai voice",
            "voice is",
            "audio quality",
            "sound effects",
            "voice extremely robotic",
            "problem in voiceover",
        ],
    ):
        sent = -1 if has_any(t, ["robotic", "problem", "bad", "extremely", "issues"]) else 0
        tags.append(("voice_audio_quality", sent))

    # --- language_support ---
    if has_any(
        t,
        [
            "in english instead of",
            "in english, instead of",
            "instead of my language",
            "instead of portuguese",
            "instead of spanish",
            "in another language",
            "could have translated",
            "translate to other languages",
            "language it wants",
            "puts the language",
            "doesn't understand either english or arabic",
            "doesn't know what you're writing in english or arabic",
            "doesn't understand english or arabic",
            "not even in my language",
            "in latin spanish",
            "generating in english",
            "generating many videos in english",
        ],
    ):
        tags.append(("language_support", -1))

    # --- loves_concept_overall (+1) — only for SHORT generic praise ---
    # Trigger when text is short, no specific feature was tagged, and contains
    # generic high praise vocabulary.
    if rating == 5 and len(t) < 80:
        if has_any(
            t,
            [
                "wonderful",
                "amazing",
                "legendary",
                "best app",
                "best ai",
                "awesome",
                "excellent",
                "fantastic",
                "love this",
                "love it",
                "i love",
                "very beautiful",
                "incredible",
                "masterpiece",
                "mythical",
                "world-class",
                "marvelous",
                "10/10",
                "thousand stars",
                "perfect",
                "splendid",
            ],
        ):
            tags.append(("loves_concept_overall", 1))

    # --- dislikes_concept_overall (-1) — only for SHORT generic dismissal ---
    if rating == 1 and len(t) < 80:
        if has_any(
            t,
            [
                "trash",
                "useless",
                "garbage",
                "worthless",
                "rubbish",
                "horrible",
                "terrible",
                "very bad",
                "very failed",
                "failed app",
                "the worst",
                "worst app",
                "i hate",
                "i don't like",
                "doesn't work at all",
                "doesn't do anything",
                "not good",
                "not a solution",
                "do not download",
            ],
        ):
            tags.append(("dislikes_concept_overall", -1))

    return tags


def main() -> None:
    if not BACKUP.exists():
        shutil.copy(JSONL, BACKUP)
        print(f"backed up to {BACKUP}")

    # Build rating lookup
    translated = json.loads(TRANSLATED.read_text())
    rating_by_id: dict[str, int | None] = {}
    for r in translated:
        try:
            rating_by_id[r["source_id"]] = int(r.get("rating") or 0) or None
        except (ValueError, TypeError):
            rating_by_id[r["source_id"]] = None

    # Read existing classifications
    rows = []
    with JSONL.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    # Apply extensions
    added_per_tag: dict[str, int] = {}
    total_added = 0
    for r in rows:
        existing_ids = {feat for feat, _ in r.get("f", [])}
        rating = rating_by_id.get(r["id"])
        new_tags = detect(r.get("en", ""), rating)
        # Dedup against existing
        for tag, sent in new_tags:
            if tag not in existing_ids:
                r.setdefault("f", []).append([tag, sent])
                existing_ids.add(tag)
                added_per_tag[tag] = added_per_tag.get(tag, 0) + 1
                total_added += 1

    # Write out
    with JSONL.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"updated {len(rows)} rows; added {total_added} new attributions")
    for tag in sorted(added_per_tag, key=lambda k: -added_per_tag[k]):
        print(f"  {tag:35s} +{added_per_tag[tag]}")


if __name__ == "__main__":
    main()
