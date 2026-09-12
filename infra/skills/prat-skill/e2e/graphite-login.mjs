// Save a Graphite V2 login once, so later screenshots run without a password.
//
//   node graphite-login.mjs
//
// A real Chrome window opens on the Graphite portal. Sign in by hand with the
// Microsoft button. The moment it sees you are through, it saves the session
// and closes itself - there is nothing to press.
// Session goes to sessions/graphite.json (chmod 600, git-ignored).
// No password is ever stored, typed by a script, or printed.
//
// Companion to omni-login.mjs; deliberately separate so the omni toolkit is
// untouched.

import fs from 'node:fs';
import path from 'node:path';
import { SESSION_DIR, openBrowser } from './lib.mjs';

const BASE = (process.env.GRAPHITE_BASE || 'https://graphite-v2-prod-fe.alphadirect.co.bw').replace(/\/$/, '');
const HOST = new URL(BASE).host;
const OUT = path.join(SESSION_DIR, 'graphite.json');
const WAIT_MINUTES = 15;

console.log(`\n  A Chrome window is opening on Graphite.`);
console.log(`  Click "Sign in with Microsoft" and pick your account.`);
console.log(`  Take as long as you need - up to ${WAIT_MINUTES} minutes.`);
console.log(`  When the portal appears, this saves itself and closes.\n`);

const browser = await openBrowser({ headless: false, channel: 'chrome', args: ['--start-maximized'] });
const context = await browser.newContext({ viewport: null });
const page = await context.newPage();
await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });

async function looksSignedIn() {
  if (page.isClosed() || !browser.isConnected()) return false;
  let s;
  try {
    s = await page.evaluate(() => ({
      host: location.host,
      path: location.pathname,
      chars: (document.body?.innerText || '').length,
      keys: [...Object.keys(window.localStorage), ...Object.keys(window.sessionStorage)],
    }));
  } catch { return false; } // mid-navigation
  if (!s || s.host !== HOST) return false;
  if (/^\/login\/?$/.test(s.path)) return false;
  if (s.chars < 400) return false;
  return s.keys.some((k) => /sanctum|token|msal|auth|account/i.test(k));
}

const deadline = Date.now() + WAIT_MINUTES * 60000;
let signedIn = false;
while (Date.now() < deadline) {
  await page.waitForTimeout(2000);
  if (page.isClosed() || !browser.isConnected()) break;
  if (!(await looksSignedIn())) continue;
  await page.waitForTimeout(3000);          // the SSO bounce briefly looks signed in
  if (await looksSignedIn()) { signedIn = true; break; }
}

if (!signedIn) {
  console.log('\n  Nothing saved - the sign-in did not complete, or the window closed early.');
  console.log('  Just run this again.\n');
  if (browser.isConnected()) await browser.close();
  process.exit(2);
}

await page.waitForTimeout(2500);
if (!(await looksSignedIn())) {
  console.log('\n  Nothing saved - Graphite bounced back to the sign-in page. Run this again.\n');
  if (browser.isConnected()) await browser.close();
  process.exit(2);
}

// sessionStorage too - the Microsoft sign-in keeps its token there and
// Playwright's normal storageState leaves it out.
const sessionStorage = await page.evaluate(() => {
  const out = {};
  for (let i = 0; i < window.sessionStorage.length; i++) {
    const k = window.sessionStorage.key(i);
    out[k] = window.sessionStorage.getItem(k);
  }
  return out;
});
const storageState = await context.storageState();
const landed = page.url();

fs.mkdirSync(SESSION_DIR, { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ savedAt: new Date().toISOString(), base: BASE, storageState, sessionStorage }, null, 2));
fs.chmodSync(OUT, 0o600);

await browser.close();
console.log(`  Signed in - landed on ${landed}`);
console.log(`  Saved: ${path.relative(process.cwd(), OUT)}`);
console.log(`  Done. Graphite screenshots will now run without asking for a password.\n`);
