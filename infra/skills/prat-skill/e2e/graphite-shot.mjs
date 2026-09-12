// Screenshot Graphite V2 pages using the session saved by graphite-login.mjs.
//
//   node graphite-shot.mjs "/claims/dashboard" out.png [--width 1440] [--wait 9000] [--viewport]
//
// Default is a full-page shot. --viewport captures just the visible window.
// Read-only: it navigates and photographs, nothing else.

import fs from 'node:fs';
import path from 'node:path';
import { SESSION_DIR, openBrowser, unmangle } from './lib.mjs';

const argv = process.argv.slice(2);
const flag = (name, dflt) => {
  const i = argv.indexOf(`--${name}`);
  return i === -1 ? dflt : argv[i + 1];
};
const positional = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && argv[i - 1].startsWith('--') && argv[i - 1] !== '--viewport'));

const route = unmangle(positional[0] || '/');
const outPath = positional[1] || 'shot.png';
const width = Number(flag('width', 1440));
const waitMs = Number(flag('wait', 9000));
const fullPage = !argv.includes('--viewport');

const sessFile = path.join(SESSION_DIR, 'graphite.json');
if (!fs.existsSync(sessFile)) {
  console.error('No Graphite session. Run:  node graphite-login.mjs');
  process.exit(1);
}
const sess = JSON.parse(fs.readFileSync(sessFile, 'utf8'));
const BASE = (process.env.GRAPHITE_BASE || sess.base || 'https://graphite-v2-prod-fe.alphadirect.co.bw').replace(/\/$/, '');

const browser = await openBrowser({ headless: true });
const context = await browser.newContext({
  storageState: sess.storageState,
  viewport: { width, height: 900 },
  deviceScaleFactor: 2,
});

// Replay sessionStorage before any page script runs - the SSO token lives there.
if (sess.sessionStorage && Object.keys(sess.sessionStorage).length) {
  await context.addInitScript((entries) => {
    for (const [k, v] of Object.entries(entries)) {
      try { window.sessionStorage.setItem(k, v); } catch {}
    }
  }, sess.sessionStorage);
}

const page = await context.newPage();
const url = BASE + (route.startsWith('/') ? route : '/' + route);
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(waitMs);

const landed = page.url();
if (/\/login\b/.test(landed)) {
  console.error(`SESSION EXPIRED - landed on ${landed}. Re-run: node graphite-login.mjs`);
  await browser.close();
  process.exit(3);
}

fs.mkdirSync(path.dirname(path.resolve(outPath)), { recursive: true });
await page.screenshot({ path: outPath, fullPage });
const bytes = fs.statSync(outPath).size;
await browser.close();

console.log(`${outPath}  ${bytes} bytes  <- ${landed}`);
