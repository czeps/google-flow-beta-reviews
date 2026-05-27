import type { FeatureRaw, FeatureSummary } from "./types";

// "Praised" = themes that users actually speak positively about, even if
// the same theme also gets complaints. Ranked by absolute positive count.
// In a beta product almost every theme has more complaints than compliments,
// but the things users DO praise are still the most appreciated parts of
// the app — and that's what this list surfaces.
//
// "Issue" = themes where negatives outnumber positives at meaningful volume.
//
// A theme can legitimately appear in BOTH lists when it's net-negative but
// has at least 5 fans (e.g. video quality, UI/UX). That's not a bug —
// it's a feature: it tells the reader "people are split on this."
//
// We deliberately do NOT use the overall star rating, because that is the
// rating of the whole review, not the user's stance on this specific theme.
const MIN_POSITIVE = 5;
const MIN_NEGATIVE = 5;

// Accept either the raw (snake_case from JSON) or the summary (camelCase)
// shape via a tiny shared shape — both end up calling the same predicates.
type SentimentCounts = { positive: number; negative: number };

export function isPraised(f: SentimentCounts): boolean {
  return f.positive >= MIN_POSITIVE;
}

export function isIssue(f: SentimentCounts): boolean {
  return f.negative >= MIN_NEGATIVE && f.negative > f.positive;
}

function rawCounts(f: FeatureRaw): SentimentCounts {
  return { positive: f.positive_count, negative: f.negative_count };
}

export function categorize(f: FeatureRaw): FeatureSummary["category"] {
  const c = rawCounts(f);
  if (isPraised(c)) return "praised";
  if (isIssue(c)) return "issue";
  return "neutral";
}

export function toSummary(f: FeatureRaw): FeatureSummary {
  return {
    id: f.feature_id,
    name: f.name,
    description: f.description,
    rating: f.avg_star_rating ?? 0,
    mentions: f.mention_count,
    positive: f.positive_count,
    negative: f.negative_count,
    neutral: f.neutral_count,
    pct_positive: f.pct_positive,
    pct_negative: f.pct_negative,
    category: categorize(f),
  };
}
