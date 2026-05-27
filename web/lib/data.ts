// Build-time data loader. Runs during `next build` in Node, never in the
// browser. Reads the snapshots in web/data/, computes one CountrySlice per
// country (plus an "all" slice) and returns the full DashboardData.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { isIssue, isPraised, toSummary } from "./sentiment";
import type {
  AttributionRaw,
  CountrySlice,
  DashboardData,
  DailyPoint,
  FeatureRaw,
  FeatureSummary,
  KPIs,
  ReviewCard,
  ReviewRaw,
  ScoreBin,
} from "./types";

const DATA = join(process.cwd(), "data");

// ISO country code -> human label.  Covers everything our scraper hits.
const COUNTRY_NAMES: Record<string, string> = {
  us: "United States", gb: "United Kingdom", ca: "Canada", au: "Australia",
  ie: "Ireland", in: "India", pk: "Pakistan", ph: "Philippines", sg: "Singapore",
  my: "Malaysia", za: "South Africa", ng: "Nigeria", ke: "Kenya", gh: "Ghana",
  es: "Spain", mx: "Mexico", ar: "Argentina", cl: "Chile", co: "Colombia",
  pe: "Peru", ve: "Venezuela", uy: "Uruguay", ec: "Ecuador", bo: "Bolivia",
  py: "Paraguay", cr: "Costa Rica", gt: "Guatemala", pa: "Panama",
  do: "Dominican Republic", sv: "El Salvador", hn: "Honduras", ni: "Nicaragua",
  pt: "Portugal", br: "Brazil", ao: "Angola", mz: "Mozambique",
  fr: "France", be: "Belgium", ch: "Switzerland", lu: "Luxembourg", mc: "Monaco",
  ma: "Morocco", dz: "Algeria", tn: "Tunisia", sn: "Senegal", ci: "Ivory Coast",
  cm: "Cameroon", ml: "Mali", bf: "Burkina Faso", mg: "Madagascar",
  de: "Germany", at: "Austria", li: "Liechtenstein",
  it: "Italy", sm: "San Marino", va: "Vatican City",
  nl: "Netherlands", sr: "Suriname",
  cv: "Cape Verde",
  sa: "Saudi Arabia", ae: "United Arab Emirates", eg: "Egypt", kw: "Kuwait",
  qa: "Qatar", bh: "Bahrain", om: "Oman", jo: "Jordan", lb: "Lebanon",
  iq: "Iraq", ye: "Yemen", ly: "Libya", sd: "Sudan", ps: "Palestine",
  tw: "Taiwan", hk: "Hong Kong", mo: "Macao",
  ru: "Russia", by: "Belarus", kz: "Kazakhstan", kg: "Kyrgyzstan",
  uz: "Uzbekistan", tj: "Tajikistan", am: "Armenia", az: "Azerbaijan",
  md: "Moldova", ua: "Ukraine",
  tr: "Turkey",
  pl: "Poland", cz: "Czechia", sk: "Slovakia", hu: "Hungary",
  ro: "Romania", bg: "Bulgaria",
  hr: "Croatia", rs: "Serbia", ba: "Bosnia & Herzegovina", si: "Slovenia",
  mk: "North Macedonia", al: "Albania",
  ee: "Estonia", lv: "Latvia", lt: "Lithuania",
  se: "Sweden", no: "Norway", dk: "Denmark", fi: "Finland", is: "Iceland",
  gr: "Greece", cy: "Cyprus",
  il: "Israel",
  id: "Indonesia", th: "Thailand", vn: "Vietnam", bn: "Brunei",
  kh: "Cambodia", la: "Laos", mm: "Myanmar",
  bd: "Bangladesh", lk: "Sri Lanka", np: "Nepal",
  jp: "Japan", kr: "South Korea",
  ge: "Georgia", mn: "Mongolia",
  et: "Ethiopia", tz: "Tanzania", ug: "Uganda", zw: "Zimbabwe",
  jm: "Jamaica", tt: "Trinidad & Tobago",
  ir: "Iran",
};

function countryLabel(slug: string): string {
  return COUNTRY_NAMES[slug] ?? slug.toUpperCase();
}

function loadJSON<T>(name: string): T {
  return JSON.parse(readFileSync(join(DATA, name), "utf8")) as T;
}

function computeKPIs(
  reviews: ReviewRaw[],
  praised: FeatureSummary[],
  issues: FeatureSummary[],
): KPIs {
  const dates = reviews.map((r) => r.date).filter((d): d is string => Boolean(d)).sort();
  const ratings = reviews.map((r) => r.rating).filter((n) => Number.isFinite(n));
  const positives = ratings.filter((n) => n >= 4).length;
  const languages = new Set(reviews.map((r) => r.lang)).size;
  return {
    total_reviews: reviews.length,
    date_range: {
      start: dates[0]?.slice(0, 10) ?? "",
      end: dates[dates.length - 1]?.slice(0, 10) ?? "",
    },
    avg_score: ratings.length
      ? Number((ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(2))
      : 0,
    pct_positive: ratings.length ? positives / ratings.length : 0,
    features_praised: praised.length,
    praised_mentions: praised.reduce((sum, f) => sum + f.mentions, 0),
    issues_count: issues.length,
    languages,
  };
}

function computeScoreBins(reviews: ReviewRaw[]): ScoreBin[] {
  const bins: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  for (const r of reviews) {
    if (r.rating >= 1 && r.rating <= 5) bins[Math.round(r.rating)] += 1;
  }
  return [1, 2, 3, 4, 5].map((s) => ({ score: s as 1 | 2 | 3 | 4 | 5, count: bins[s] }));
}

function computeDaily(reviews: ReviewRaw[]): DailyPoint[] {
  const by: Record<string, { sum: number; n: number }> = {};
  for (const r of reviews) {
    if (!r.date || !Number.isFinite(r.rating)) continue;
    const day = r.date.slice(0, 10);
    if (!by[day]) by[day] = { sum: 0, n: 0 };
    by[day].sum += r.rating;
    by[day].n += 1;
  }
  return Object.entries(by)
    .map(([date, { sum, n }]) => ({ date, avg: Number((sum / n).toFixed(2)), count: n }))
    .sort((a, b) => (a.date < b.date ? -1 : 1));
}

// Recompute per-feature stats from raw attributions joined with the country
// slice of reviews. This makes country slicing accurate -- if we just filtered
// the precomputed features table we'd keep counts from the whole corpus.
function computeFeatures(
  features: FeatureRaw[],
  attributions: AttributionRaw[],
  reviewIds: Set<string>,
  ratingsById: Map<string, number>,
): FeatureSummary[] {
  const meta = new Map(features.map((f) => [f.feature_id, f]));
  const agg: Record<string, { pos: number; neg: number; neu: number; mentions: Set<string>; ratings: number[] }> = {};

  for (const a of attributions) {
    if (a.feature === "_none") continue;
    if (!reviewIds.has(a.id)) continue;
    if (!agg[a.feature]) agg[a.feature] = { pos: 0, neg: 0, neu: 0, mentions: new Set(), ratings: [] };
    const slot = agg[a.feature];
    slot.mentions.add(a.id);
    if (a.sentiment === 1) slot.pos += 1;
    else if (a.sentiment === -1) slot.neg += 1;
    else slot.neu += 1;
    const r = ratingsById.get(a.id);
    if (r !== undefined) slot.ratings.push(r);
  }

  const summaries: FeatureSummary[] = [];
  for (const [id, slot] of Object.entries(agg)) {
    const m = meta.get(id);
    if (!m) continue;
    const total = slot.pos + slot.neg + slot.neu;
    const mentions = slot.mentions.size;
    const rating = slot.ratings.length
      ? slot.ratings.reduce((a, b) => a + b, 0) / slot.ratings.length
      : 0;
    summaries.push(
      toSummary({
        ...m,
        mention_count: mentions,
        positive_count: slot.pos,
        negative_count: slot.neg,
        neutral_count: slot.neu,
        avg_star_rating: Number(rating.toFixed(2)),
        pct_positive: total ? slot.pos / total : 0,
        pct_negative: total ? slot.neg / total : 0,
      }),
    );
  }
  return summaries;
}

function buildReviewsByFeature(
  attributions: AttributionRaw[],
  reviewsById: Map<string, ReviewRaw>,
): Record<string, ReviewCard[]> {
  const buckets: Record<string, ReviewCard[]> = {};
  for (const a of attributions) {
    if (a.feature === "_none") continue;
    if (a.sentiment === 0) continue; // drawers only surface +/-
    const review = reviewsById.get(a.id);
    if (!review) continue;
    const key = `${a.feature}:${a.sentiment === 1 ? "positive" : "negative"}`;
    if (!buckets[key]) buckets[key] = [];
    buckets[key].push({
      id: review.id,
      rating: review.rating,
      date: review.date,
      country: review.country,
      lang: review.lang,
      body_en: review.body_en,
      thumbs: review.thumbs,
    });
  }
  // Sort each bucket. Praised: highest rating first; issues: lowest first.
  // Both fall back to thumbs desc then date desc.
  for (const [key, cards] of Object.entries(buckets)) {
    const isPos = key.endsWith(":positive");
    cards.sort((a, b) => {
      const r = isPos ? b.rating - a.rating : a.rating - b.rating;
      if (r !== 0) return r;
      if (b.thumbs !== a.thumbs) return b.thumbs - a.thumbs;
      return (b.date ?? "").localeCompare(a.date ?? "");
    });
  }
  return buckets;
}

function buildSlice(
  slug: string,
  label: string,
  reviews: ReviewRaw[],
  attributions: AttributionRaw[],
  features: FeatureRaw[],
): CountrySlice {
  const ids = new Set(reviews.map((r) => r.id));
  const ratingsById = new Map(reviews.map((r) => [r.id, r.rating]));
  const reviewsById = new Map(reviews.map((r) => [r.id, r]));
  const all = computeFeatures(features, attributions, ids, ratingsById);

  // A theme can appear in both lists when it's net-negative AND has ≥5 fans
  // (e.g. UI/UX, video quality). The categorize() helper picks ONE bucket for
  // the unique `category` tag on each summary, but the lists themselves
  // re-filter independently so overlap is allowed.
  const praised = all
    .filter((f) => isPraised(f))
    .sort((a, b) => b.positive - a.positive);
  const issues = all
    .filter((f) => isIssue(f))
    .sort((a, b) => b.negative - a.negative);

  // reviewsByFeature is built per-slice from the attributions filtered to this
  // slice's review IDs. Same fact joined two ways: aggregate counts (above)
  // and individual cards (here).
  const sliceAttributions = attributions.filter((a) => ids.has(a.id));
  const reviewsByFeature = buildReviewsByFeature(sliceAttributions, reviewsById);

  return {
    slug,
    label,
    count: reviews.length,
    kpis: computeKPIs(reviews, praised, issues),
    scores: computeScoreBins(reviews),
    daily: computeDaily(reviews),
    praised,
    issues,
    reviewsByFeature,
  };
}

let cache: DashboardData | null = null;

export function getDashboardData(): DashboardData {
  if (cache) return cache;

  const features = loadJSON<FeatureRaw[]>("features.json");
  const reviews = loadJSON<ReviewRaw[]>("reviews.slim.json");
  const attributions = loadJSON<AttributionRaw[]>("review-features.json");

  // Group by country.
  const byCountry = new Map<string, ReviewRaw[]>();
  for (const r of reviews) {
    const c = r.country ?? "unknown";
    if (!byCountry.has(c)) byCountry.set(c, []);
    byCountry.get(c)!.push(r);
  }

  const slices: Record<string, CountrySlice> = {
    all: buildSlice("all", "All countries", reviews, attributions, features),
  };
  for (const [code, list] of byCountry) {
    slices[code] = buildSlice(code, countryLabel(code), list, attributions, features);
  }

  const countries = [
    { slug: "all", label: "All countries", count: reviews.length },
    ...[...byCountry.entries()]
      .map(([code, list]) => ({ slug: code, label: countryLabel(code), count: list.length }))
      .sort((a, b) => b.count - a.count),
  ];

  cache = {
    source: { id: "google_play", label: "Google Play" },
    slices,
    countries,
  };
  return cache;
}
