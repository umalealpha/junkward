// Crawl a website and photograph every page it finds.
//
//   node web-crawl.mjs https://www.alphadirect.co.bw --depth 2 --max 40
//   node web-crawl.mjs https://omni.alphadirect.co.bw/dashboard --as staff --depth 2
//   node web-crawl.mjs https://example.com --max 20 --same-origin false
//
// --depth         how many clicks deep to follow (default 2)
// --max           stop after this many pages (default 40)
// --as            admin | staff | anon   (default anon; use a role for omni)
// --width         viewport width (default 1280)
// --same-origin   true (default) keeps it on one domain
// --allow         extra regex a URL must match to be followed
// --jobs          how many pages at once (default 4)
// --no-robots     skip the robots.txt check (only for sites you own)
//
// Writes: a JSON report, one PNG per page, and a contact sheet of the lot.

import fs from 'node:fs';
import path from 'node:path';
import {
  openBrowser, newRolePage, settle, shoot, verdict, contactSheet, isProblem,
  parseArgs, SHOT_DIR, slug, stamp,
} from './lib.mjs';

// "https://x.com" and "https://x.com/" are the same page - treat them as one.
const canon = (u) => {
  const url = new URL(u);
  url.hash = '';
  if (url.pathname === '') url.pathname = '/';
  return url.toString();
};

const { positional, flags } = parseArgs(process.argv.slice(2));
const start = positional[0];
if (!start) {
  console.error('Usage: node web-crawl.mjs <start url> [--depth 2] [--max 40] [--as anon] [--width 1280]');
  process.exit(1);
}

const maxDepth = Number(flags.depth ?? 2);
const maxPages = Number(flags.max ?? 40);
const role = (flags.as || 'anon').toLowerCase();
const width = Number(flags.width || 1280);
const jobs = Number(flags.jobs || 4);
const sameOrigin = String(flags['same-origin'] ?? 'true') !== 'false';
const allow = flags.allow ? new RegExp(flags.allow) : null;
const checkRobots = !process.argv.includes('--no-robots');

const origin = new URL(start).origin;
const runId = `crawl-${slug(new URL(start).hostname)}-${stamp()}`;
const dir = path.join(SHOT_DIR, runId);

// Be polite on sites we don't own: honour robots.txt Disallow rules.
let disallowed = [];
if (checkRobots) {
  try {
    const res = await fetch(`${origin}/robots.txt`, { signal: AbortSignal.timeout(10000) });
    if (res.ok) {
      let appliesToUs = false;
      for (const line of (await res.text()).split('\n')) {
        const [rawKey, ...rest] = line.split('#')[0].split(':');
        const key = rawKey.trim().toLowerCase();
        const val = rest.join(':').trim();
        if (key === 'user-agent') appliesToUs = val === '*';
        else if (key === 'disallow' && appliesToUs && val) disallowed.push(val);
      }
      if (disallowed.length) console.log(`  robots.txt: honouring ${disallowed.length} disallow rule(s)`);
    }
  } catch { /* no robots.txt is fine */ }
}

const blockedByRobots = (u) => {
  const p = new URL(u).pathname;
  return disallowed.some((d) => p.startsWith(d));
};

const seen = new Set();
const queue = [{ url: start, depth: 0 }];
const results = [];

const browser = await openBrowser();
console.log(`\n  Crawling ${start}  (depth ${maxDepth}, max ${maxPages} pages, as ${role})\n`);

while (queue.length && results.length < maxPages) {
  const batch = [];
  while (queue.length && batch.length < jobs && results.length + batch.length < maxPages) {
    const item = queue.shift();
    const key = canon(item.url);
    if (seen.has(key)) continue;
    seen.add(key);
    batch.push({ ...item, url: key });
  }
  if (!batch.length) break;

  const done = await Promise.all(batch.map(visit));
  for (const r of done) {
    results.push(r);
    console.log(`  ${r.state.padEnd(9)} ${String(r.status ?? '---').padEnd(4)} d${r.depth} ${r.url}`);
    for (const link of r.newLinks) queue.push({ url: link, depth: r.depth + 1 });
  }
}

await browser.close();

async function visit({ url, depth }) {
  const { context, page, consoleErrors } = await newRolePage(browser, {
    role, width, anonymous: role === 'anon',
  });
  try {
    const res = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await settle(page);
    const status = res ? res.status() : null;

    const file = path.join(dir, `${String(results.length + 1).padStart(3, '0')}-${slug(url)}.png`);
    await shoot(page, file);

    const title = await page.title().catch(() => '');
    const text = ((await page.locator('body').innerText().catch(() => '')) || '')
      .replace(/\s+/g, ' ').trim();
    const v = await verdict(page, status, consoleErrors);

    let newLinks = [];
    if (depth < maxDepth) {
      const hrefs = await page.$$eval('a[href]', (as) => as.map((a) => a.href));
      newLinks = [...new Set(hrefs)]
        .filter((h) => /^https?:/.test(h))
        .map(canon)
        .filter((h) => !sameOrigin || new URL(h).origin === origin)
        .filter((h) => !allow || allow.test(h))
        .filter((h) => !blockedByRobots(h))
        .filter((h) => !seen.has(h));
    }

    return { url, depth, status, title, ...v, file, chars: text.length, excerpt: text.slice(0, 400), newLinks };
  } catch (err) {
    return {
      url, depth, status: null, state: 'BROKEN', why: String(err.message).split('\n')[0],
      title: '', file: null, chars: 0, excerpt: '', newLinks: [],
    };
  } finally {
    await context.close();
  }
}

const report = path.join(SHOT_DIR, `${runId}.json`);
fs.writeFileSync(report, JSON.stringify({
  start, role, width, maxDepth, when: new Date().toISOString(),
  pages: results.map(({ newLinks, ...r }) => r),
}, null, 2));

const sheet = path.join(SHOT_DIR, `${runId}.png`);
await contactSheet(
  results.filter((r) => r.file).map((r) => ({
    file: r.file, caption: r.title || r.url, state: r.state,
    note: new URL(r.url).pathname + (r.why ? `  -  ${r.why}` : ''),
  })),
  sheet,
  { title: `${start}  -  ${results.length} pages`, columns: 3, width: 2200 }
);

const bad = results.filter((r) => isProblem(r.state));
const noisy = results.filter((r) => r.state === 'OK*').length;
console.log(`\n  ${results.length} pages, ${results.length - bad.length} fine${noisy ? ` (${noisy} with console errors)` : ''}, ${bad.length} needing a look.`);
console.log(`  Every page in one picture: ${sheet}`);
console.log(`  Text + status report:      ${report}`);
console.log(`  Individual screenshots:    ${dir}\n`);
process.exitCode = bad.some((b) => ['BROKEN', 'BLANK'].includes(b.state)) ? 1 : 0;
