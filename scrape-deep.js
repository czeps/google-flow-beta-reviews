import gplay from 'google-play-scraper';
import fs from 'node:fs/promises';
import path from 'node:path';

const APP_ID = 'com.google.android.apps.labs.whisk';
const OUT_DIR = path.resolve('./out');
const NUM_HINT = 5000;
const SORTS = [
  { name: 'NEWEST', value: gplay.sort.NEWEST },
  { name: 'RATING', value: gplay.sort.RATING },
  { name: 'HELPFULNESS', value: gplay.sort.HELPFULNESS },
];
const COUNTRIES = (process.env.COUNTRIES || 'us').split(',');
const LANGS = (process.env.LANGS || 'en').split(',');
const MAX_PAGES = parseInt(process.env.MAX_PAGES || '500', 10);

async function deepFetch({ country, lang, sort }) {
  const seen = new Map();
  let token = undefined;
  let page = 0;
  let consecutiveNoNew = 0;
  while (page < MAX_PAGES) {
    page += 1;
    const args = {
      appId: APP_ID, country, lang, sort: sort.value, num: NUM_HINT,
    };
    if (token) args.paginate = true, args.nextPaginationToken = token;
    let res;
    try {
      res = await gplay.reviews(args);
    } catch (e) {
      console.log(`   ! err on page ${page}: ${e.message}`);
      break;
    }
    const data = res?.data || (Array.isArray(res) ? res : []);
    const before = seen.size;
    for (const r of data) seen.set(r.id, r);
    const added = seen.size - before;
    const nextTok = res?.nextPaginationToken;
    console.log(`   p${page}: got=${data.length} new=${added} total=${seen.size} token=${nextTok ? 'yes' : 'NO'}`);
    if (!nextTok) break;
    if (added === 0) {
      consecutiveNoNew += 1;
      if (consecutiveNoNew >= 3) {
        console.log('   stopping: 3 pages with zero new reviews');
        break;
      }
    } else consecutiveNoNew = 0;
    token = nextTok;
    await new Promise((r) => setTimeout(r, 250));
  }
  return [...seen.values()];
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const merged = new Map();
  for (const country of COUNTRIES) {
    for (const lang of LANGS) {
      for (const sort of SORTS) {
        console.log(`\n== ${country}/${lang}/${sort.name} ==`);
        const reviews = await deepFetch({ country: country.trim(), lang: lang.trim(), sort });
        for (const r of reviews) merged.set(r.id, r);
        console.log(`  combo done. universe so far: ${merged.size}`);
      }
    }
  }
  const all = [...merged.values()].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );
  await fs.writeFile(path.join(OUT_DIR, 'reviews.json'), JSON.stringify(all, null, 2));
  const dates = all.map((x) => new Date(x.date));
  const min = new Date(Math.min(...dates));
  const max = new Date(Math.max(...dates));
  console.log(`\nTOTAL UNIQUE: ${all.length}`);
  console.log(`date range:   ${min.toISOString()}  →  ${max.toISOString()}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
