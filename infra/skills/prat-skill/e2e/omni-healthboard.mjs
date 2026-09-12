// Sweep omni's pages and flag anything broken, blank, spinning or blocked.
//
//   node omni-healthboard.mjs                       <- the 32 pages in pages.json, as staff
//   node omni-healthboard.mjs --as admin
//   node omni-healthboard.mjs --from mylist.json
//   node omni-healthboard.mjs --from-repo C:/Users/PrathapAsus/work/alpha-finance
//
// Prints a table, writes a JSON report, and stitches the bad ones into one picture.

import fs from 'node:fs';
import path from 'node:path';
import {
  openBrowser, newRolePage, gotoPath, shoot, verdict, contactSheet, isProblem,
  parseArgs, HERE, SHOT_DIR, slug, stamp,
} from './lib.mjs';

const runStamp = stamp();

const { flags } = parseArgs(process.argv.slice(2));
const role = (flags.as || 'staff').toLowerCase();
const width = Number(flags.width || 1120);
const concurrency = Number(flags.jobs || 4);

let pages;
if (flags['from-repo']) {
  // Every real page route in the Next.js app, minus the dynamic [id] ones.
  const appDir = path.join(flags['from-repo'], 'frontend', 'src', 'app');
  pages = walk(appDir)
    .filter((f) => path.basename(f) === 'page.tsx')
    .map((f) => '/' + path.relative(appDir, path.dirname(f)).split(path.sep).join('/'))
    .map((r) => r.replace(/\/\([^)]+\)/g, ''))
    .filter((r) => !r.includes('[') && r !== '/')
    .sort();
} else {
  pages = JSON.parse(fs.readFileSync(flags.from || path.join(HERE, 'pages.json'), 'utf8'));
}

console.log(`\n  Sweeping ${pages.length} pages as ${role} at ${width}px...\n`);

const dir = path.join(SHOT_DIR, `health-${role}-${runStamp}`);
const browser = await openBrowser();
const results = [];

for (let i = 0; i < pages.length; i += concurrency) {
  const batch = pages.slice(i, i + concurrency);
  const done = await Promise.all(batch.map((p) => check(p)));
  for (const r of done) {
    results.push(r);
    console.log(`  ${r.state.padEnd(9)} ${String(r.status ?? '---').padEnd(4)} ${r.page}${r.why ? '   (' + r.why + ')' : ''}`);
  }
}

await browser.close();

async function check(target) {
  const { context, page, consoleErrors } = await newRolePage(browser, { role, width, anonymous: role === 'anon' });
  try {
    const { status } = await gotoPath(page, target);
    const file = path.join(dir, `${slug(target)}.png`);
    await shoot(page, file);
    const v = await verdict(page, status, consoleErrors);
    return { page: target, status, ...v, file };
  } catch (err) {
    return { page: target, status: null, state: 'BROKEN', why: String(err.message).split('\n')[0], file: null };
  } finally {
    await context.close();
  }
}

function walk(dir) {
  if (!fs.existsSync(dir)) throw new Error(`No such folder: ${dir}`);
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const full = path.join(dir, e.name);
    return e.isDirectory() ? walk(full) : [full];
  });
}

const bad = results.filter((r) => isProblem(r.state));
const report = path.join(SHOT_DIR, `health-${role}-${runStamp}.json`);
fs.writeFileSync(report, JSON.stringify({ role, width, when: new Date().toISOString(), results }, null, 2));

console.log(`\n  ${results.length - bad.length}/${results.length} fine, ${bad.length} needing a look.`);
if (bad.length) {
  const sheet = path.join(SHOT_DIR, `health-${role}-${runStamp}-problems.png`);
  await contactSheet(
    bad.filter((b) => b.file).map((b) => ({ file: b.file, caption: b.page, state: b.state, note: b.why })),
    sheet,
    { title: `omni pages needing a look  -  as ${role}, ${width}px`, columns: 2, width: 1800 }
  );
  console.log(`  Problem pages in one picture: ${sheet}`);
}
console.log(`  Full report: ${report}`);
console.log(`  All screenshots: ${dir}\n`);
process.exitCode = bad.some((b) => ['BROKEN', 'BLANK'].includes(b.state)) ? 1 : 0;
