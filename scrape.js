import gplay from 'google-play-scraper';
import fs from 'node:fs/promises';
import path from 'node:path';

const APP_ID = 'com.google.android.apps.labs.whisk';
const OUT_DIR = path.resolve('./out');
const PAGE_SIZE = 150;
const SORTS = [
  { name: 'NEWEST', value: gplay.sort.NEWEST },
  { name: 'RATING', value: gplay.sort.RATING },
  { name: 'HELPFULNESS', value: gplay.sort.HELPFULNESS },
];
const LANGS = (process.env.LANGS || 'en').split(',').map((s) => s.trim());
const COUNTRIES = (process.env.COUNTRIES || 'us').split(',').map((s) => s.trim());

async function fetchAll({ lang, country, sort }) {
  const all = new Map();
  let nextToken = null;
  let page = 0;
  do {
    const res = await gplay.reviews({
      appId: APP_ID,
      lang,
      country,
      sort: sort.value,
      num: PAGE_SIZE,
      paginate: true,
      nextPaginationToken: nextToken,
    });
    page += 1;
    const data = res.data || [];
    for (const r of data) all.set(r.id, r);
    nextToken = res.nextPaginationToken || null;
    process.stdout.write(
      `  [${country}/${lang}/${sort.name}] page ${page}: +${data.length} (total unique: ${all.size})${nextToken ? '' : ' (end)'}\n`,
    );
    if (!nextToken || data.length === 0) break;
  } while (true);
  return [...all.values()];
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });

  console.log(`Fetching app metadata for ${APP_ID}...`);
  const app = await gplay.app({ appId: APP_ID });
  await fs.writeFile(path.join(OUT_DIR, 'app.json'), JSON.stringify(app, null, 2));
  console.log(`  title: ${app.title} | rating: ${app.score} | reviews count (claimed): ${app.reviews}`);

  const merged = new Map();
  for (const country of COUNTRIES) {
    for (const lang of LANGS) {
      for (const sort of SORTS) {
        console.log(`\nScraping country=${country} lang=${lang} sort=${sort.name}`);
        try {
          const reviews = await fetchAll({ lang, country, sort });
          for (const r of reviews) merged.set(r.id, r);
        } catch (err) {
          console.error(`  error: ${err.message}`);
        }
      }
    }
  }

  const reviews = [...merged.values()].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );

  const jsonPath = path.join(OUT_DIR, 'reviews.json');
  await fs.writeFile(jsonPath, JSON.stringify(reviews, null, 2));

  const csvPath = path.join(OUT_DIR, 'reviews.csv');
  const headers = ['id', 'userName', 'score', 'date', 'thumbsUp', 'replyDate', 'version', 'text', 'replyText', 'url'];
  const escape = (v) => {
    if (v === null || v === undefined) return '';
    const s = String(v).replace(/"/g, '""');
    return `"${s}"`;
  };
  const lines = [headers.join(',')];
  for (const r of reviews) {
    lines.push(
      [
        r.id,
        r.userName,
        r.score,
        r.date,
        r.thumbsUp,
        r.replyDate,
        r.version,
        r.text,
        r.replyText,
        r.url,
      ]
        .map(escape)
        .join(','),
    );
  }
  await fs.writeFile(csvPath, lines.join('\n'));

  console.log(`\nDone. Unique reviews: ${reviews.length}`);
  console.log(`  JSON: ${jsonPath}`);
  console.log(`  CSV : ${csvPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
