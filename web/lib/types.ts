export type FeatureRaw = {
  feature_id: string;
  name: string;
  description: string;
  mention_count: number;
  avg_star_rating: number | null;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  pct_positive: number;
  pct_negative: number;
  top_quotes_en: string;
  top_quotes_orig: string;
};

export type ReviewRaw = {
  id: string;
  country: string | null;
  rating: number;
  date: string | null;
  body: string;
  body_en: string;
  lang: string;
  thumbs: number;
};

export type AttributionRaw = {
  id: string;
  feature: string;
  sentiment: number;
};

export type KPIs = {
  total_reviews: number;
  date_range: { start: string; end: string };
  avg_score: number;
  pct_positive: number;
  features_praised: number;
  praised_mentions: number;
  issues_count: number;
  languages: number;
};

export type ReviewCard = {
  id: string;
  rating: number;
  date: string | null;
  country: string | null;
  lang: string;
  body_en: string;
  thumbs: number;
};

export type ScoreBin = { score: 1 | 2 | 3 | 4 | 5; count: number };

export type DailyPoint = { date: string; avg: number; count: number };

export type FeatureSummary = {
  id: string;
  name: string;
  description: string;
  rating: number;
  mentions: number;
  positive: number;
  negative: number;
  neutral: number;
  pct_positive: number;
  pct_negative: number;
  category: "praised" | "issue" | "neutral";
};

export type CountrySlice = {
  slug: string; // "all" or country code
  label: string; // "All countries", "United States"
  count: number;
  kpis: KPIs;
  scores: ScoreBin[];
  daily: DailyPoint[];
  praised: FeatureSummary[];
  issues: FeatureSummary[];
  // Keyed by `${feature_id}:${"positive"|"negative"}` — drives the click-to-
  // expand drawer that lists the reviews behind each row.
  reviewsByFeature: Record<string, ReviewCard[]>;
};

export type DashboardData = {
  source: { id: "google_play"; label: "Google Play" };
  slices: Record<string, CountrySlice>;
  countries: Array<{ slug: string; label: string; count: number }>;
};
