// Save a login once, so every later screenshot runs without typing a password.
//
//   node omni-login.mjs staff     <- the omni@ finance-manager test account
//   node omni-login.mjs admin     <- the CFO's own Microsoft sign-in
//
// A real Chrome window opens. Sign in by hand (including the emailed code).
// The moment it sees you are through, it saves the session and closes itself -
// there is nothing to press. The session goes to sessions/<role>.json.
// No password is ever stored, typed by a script, or printed.

import fs from 'node:fs';
import path from 'node:path';
import { BASE, SESSION_DIR, sessionPath, ROLES, openBrowser } from './lib.mjs';

const role = (process.argv[2] || '').toLowerCase();
if (!ROLES[role]) {
  console.error('Usage: node omni-login.mjs <admin|staff>');
  process.exit(1);
}

const WAIT_MINUTES = 15;
const startUrl = role === 'staff' ? `${BASE}/staff-login` : `${BASE}/`;

console.log(`\n  A Chrome window is opening. Sign in as ${ROLES[role].label}.`);
console.log(`  Take as long as you need - up to ${WAIT_MINUTES} minutes.`);
console.log(`  When the omni dashboard appears, this saves itself and the window closes.\n`);

// Headed mode: prefer the real Chrome already on this PC. Playwright's own
// Chromium refuses to open a visible window here ("spawn UNKNOWN").
const browser = await openBrowser({ headless: false, channel: 'chrome', args: ['--start-maximized'] });
const context = await browser.newContext({ viewport: null });
const page = await context.newPage();
await page.goto(startUrl, { waitUntil: 'domcontentloaded' });

const OMNI_HOST = new URL(BASE).host;

// The Microsoft sign-in bounces through several redirects, and omni itself
// briefly looks "logged in" mid-bounce. So a single good reading is not
// enough - require two in a row, three seconds apart, before saving.
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
  if (!s || s.host !== OMNI_HOST) return false;
  if (/^\/(login|staff-login|break-glass)\/?$/.test(s.path)) return false;
  if (s.chars < 400) return false;
  return s.keys.some((k) => /token|msal|auth|account/i.test(k));
}

const deadline = Date.now() + WAIT_MINUTES * 60000;
let signedIn = false;

while (Date.now() < deadline) {
  await page.waitForTimeout(2000);
  if (page.isClosed() || !browser.isConnected()) break;
  if (!(await looksSignedIn())) continue;
  await page.waitForTimeout(3000);
  if (await looksSignedIn()) { signedIn = true; break; }
}

if (!signedIn) {
  console.log('\n  Nothing was saved - the sign-in did not complete in time,');
  console.log('  or the window was closed early. Just run this again.\n');
  if (browser.isConnected()) await browser.close();
  process.exit(2);
}

await page.waitForTimeout(2500); // let the dashboard finish settling

// Last guard: if the app bounced us back out during that pause, save nothing.
if (!(await looksSignedIn())) {
  console.log('\n  Nothing saved - omni bounced back to the sign-in page. Run this again.\n');
  if (browser.isConnected()) await browser.close();
  process.exit(2);
}

// Grab sessionStorage too - the Microsoft sign-in keeps its token there and
// Playwright's normal save leaves it out.
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
const out = sessionPath(role);
fs.writeFileSync(out, JSON.stringify({ role, savedAt: new Date().toISOString(), storageState, sessionStorage }, null, 2));
fs.chmodSync(out, 0o600);

await browser.close();

console.log(`  Signed in - landed on ${landed}`);
console.log(`  Saved: ${path.relative(process.cwd(), out)}`);
console.log(`  Done. Screenshots will now run without asking for a password.\n`);
