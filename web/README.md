# Google Flow Beta — Review Insights dashboard

Next.js 16 (App Router) + Tailwind 4 + shadcn/ui + Recharts.
Mirrors the design of `cezary-app-reviews-production.up.railway.app` using
the 557 Google Play reviews scraped at the repo root.

## Local development

```bash
cd web
npm install
node scripts/sync-data.mjs   # snapshots ../out/ into ./data/
npm run dev                  # http://localhost:3000
```

## Refreshing the data

After running the Python pipeline (`../out/*`), re-sync:

```bash
node scripts/sync-data.mjs
git add data/*.json
git commit -m "refresh dashboard data"
```

The dashboard is fully static; the JSON snapshots are inlined at build time
(`lib/data.ts`), no runtime database or API.

## Deploying to Vercel

1. New project from this Git repo.
2. **Root Directory** → `web` (project settings → General).
3. No environment variables.
4. Auto-detected as Next.js; defaults are correct (`next build`, output static).
5. First deploy → preview URL; promote to production once it looks right.

## What's on the dashboard

- 4 KPI cards: total reviews, average score, features praised, languages.
- Score distribution bar chart (1★ → 5★, sentiment-coloured).
- Daily trends scatter chart (one dot per day, sized by review volume).
- "Most appreciated features" list, full width since Top Issues is skipped
  this iteration.
- Filter pills: static `Google Play` source + country selector (26 slices).

## What's intentionally not included yet

- **Top issues to fix** list. The `categorize()` helper in `lib/sentiment.ts`
  already classifies features as `praised`/`issue`/`neutral`; the issue list
  just isn't rendered. Add a second `<FeatureList />` to
  `components/dashboard.tsx` to enable it.
- **Click-to-expand reviews per feature.** Reviews are already snapshotted
  (`data/reviews.slim.json`, `data/review-features.json`); wire a modal or
  drawer to `<FeatureRow />` when needed.
- **Source switcher.** Pill is static (`Google Play` only). Add App Store
  data to the pipeline and the pill becomes a `<Select>` mirroring
  `CountryFilter`.
