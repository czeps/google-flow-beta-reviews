#!/usr/bin/env node
// Copy + slim the analysis outputs from ../out/ into ./data/ for the dashboard.
// Run locally whenever the Python pipeline produces new data, then commit.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = resolve(__dirname, "..");
const REPO_ROOT = resolve(WEB_ROOT, "..");
const OUT = join(REPO_ROOT, "out");
const DATA = join(WEB_ROOT, "data");

mkdirSync(DATA, { recursive: true });

// 1. features.json passes through unchanged
const features = JSON.parse(readFileSync(join(OUT, "features.json"), "utf8"));
writeFileSync(join(DATA, "features.json"), JSON.stringify(features));

// 2. play_store_translated.json -> reviews.slim.json (drop raw_json, url)
const raw = JSON.parse(readFileSync(join(OUT, "play_store_translated.json"), "utf8"));
const slim = raw.map((r) => ({
  id: r.source_id,
  country: r.country,
  rating: Number(r.rating),
  date: r.date_iso,
  body: r.body || "",
  body_en: r.body_en || r.body || "",
  lang: r.lang_detected || "en",
  thumbs: Number(r.score_or_upvotes) || 0,
}));
writeFileSync(join(DATA, "reviews.slim.json"), JSON.stringify(slim));

// 3. review_features.csv -> review-features.json
const csv = readFileSync(join(OUT, "review_features.csv"), "utf8");
const lines = csv.split("\n").filter(Boolean);
const [, ...rows] = lines;
const attributions = rows.map((line) => {
  const [source_id, feature_id, sentiment] = line.split(",");
  return { id: source_id, feature: feature_id, sentiment: Number(sentiment) };
});
writeFileSync(join(DATA, "review-features.json"), JSON.stringify(attributions));

console.log(`synced -> ${DATA}`);
console.log(`  features.json        ${features.length} features`);
console.log(`  reviews.slim.json    ${slim.length} reviews`);
console.log(`  review-features.json ${attributions.length} attributions`);
