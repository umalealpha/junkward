/**
 * omni-shot.mjs — screenshot a REAL, authenticated omni page (no SSO/MFA).
 *
 * omni authorises the browser via a DRF token in localStorage('alpha_token'),
 * so a headless browser with a valid token renders the live page exactly as a
 * signed-in user sees it — the SSO login screen is only the way that token is
 * normally obtained. Token comes from OMNI_TOKEN or ~/.omni-e2e-token (0600);
 * it is NEVER printed.
 *
 *   node omni-shot.mjs "/hris/monthly-feedback" out.png [--width 1280] [--dark]
 */
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const route = process.argv[2] || '/dashboard';
const out = process.argv[3] || 'omni-shot.png';
const widthArg = process.argv.indexOf('--width');
const width = widthArg > -1 ? parseInt(process.argv[widthArg + 1], 10) : 1280;
const dark = process.argv.includes('--dark');
// --click "Button text" (repeatable): before shooting, click each element by
// its visible text, in order — so we can OPEN a modal/popup and photograph it,
// not just the page behind it. This is the piece that catches modal/layout
// bugs like the audit "New Finding" cut-off (Oprah Phase-2, 2026-07-24) that a
// static page shot would miss entirely.
const clicks = process.argv.reduce((acc, a, i) => {
  if (a === '--click' && process.argv[i + 1]) acc.push(process.argv[i + 1]);
  return acc;
}, []);
const BASE = process.env.OMNI_BASE || 'https://omni.alphadirect.co.bw';

let token = process.env.OMNI_TOKEN;
if (!token) {
  try { token = readFileSync(join(homedir(), '.omni-e2e-token'), 'utf8').trim() } catch {}
}
if (!token) { console.error('NO_TOKEN: set OMNI_TOKEN or ~/.omni-e2e-token'); process.exit(2) }

const b = await chromium.launch();
const ctx = await b.newContext({
  viewport: { width, height: 900 },
  deviceScaleFactor: 2,
  colorScheme: dark ? 'dark' : 'light',
});
// inject the token before any app code runs (same as route-sweep)
await ctx.addInitScript(t => localStorage.setItem('alpha_token', t), token);
// OMNI_LS_EXTRA='{"key":"value"}' seeds more localStorage before app code runs —
// needed for modes the app reads from storage, e.g. the /qa read-only view flag.
if (process.env.OMNI_LS_EXTRA) {
  const extra = JSON.parse(process.env.OMNI_LS_EXTRA);
  await ctx.addInitScript(kv => {
    for (const [k, v] of Object.entries(kv)) localStorage.setItem(k, v);
  }, extra);
}
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', e => errs.push(String(e).slice(0, 200)));

try {
  await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 45000 });
  // if the token was rejected the app bounces to the SSO/login screen
  if (/\/login|\/signin|microsoftonline/i.test(page.url())) {
    console.error('AUTH_FAILED: redirected to login — token invalid/expired');
    process.exit(3);
  }
  // let client-side data loads + animations settle (the app fetches after mount)
  try { await page.waitForLoadState('networkidle', { timeout: 15000 }) } catch {}
  await page.waitForTimeout(9000);
  // Dismiss any blocking modal (e.g. the login task-reminder popup) so it doesn't
  // cover the page we're capturing.
  try { await page.keyboard.press('Escape') } catch {}
  // Strip the CFO's global "tasks need your action" login popup (+ its backdrop)
  // so it doesn't cover the page we're capturing. Targets that overlay only.
  try {
    await page.evaluate(() => {
      const hit = [...document.querySelectorAll('div')]
        .find(d => /need your action/i.test(d.textContent || '') && d.offsetParent);
      if (hit) {
        let n = hit;
        for (let i = 0; i < 8 && n; i++) {
          const cs = getComputedStyle(n);
          if (cs.position === 'fixed' || parseInt(cs.zIndex || '0', 10) >= 40) { n.remove(); break; }
          n = n.parentElement;
        }
      }
      document.querySelectorAll('.fixed.inset-0,[class*="backdrop"],[class*="overlay"]')
        .forEach(e => { const t = e.textContent || ''; if (!/commission|agent|month/i.test(t)) e.remove(); });
    });
  } catch {}
  await page.waitForTimeout(3000);
  try { await page.waitForLoadState('networkidle', { timeout: 8000 }) } catch {}
  // Slow / access-gated pages (e.g. HRIS) fetch their content after mount — if the
  // pane is still near-empty, wait once more so we capture the loaded page, not a
  // blank one. If it stays blank, flag it in the output.
  const mainLen = () => page.evaluate(() => ((document.querySelector('main') || document.body).innerText || '').replace(/\s+/g, ' ').trim().length);
  let blank = (await mainLen()) < 120;
  if (blank) { await page.waitForTimeout(6000); try { await page.waitForLoadState('networkidle', { timeout: 6000 }) } catch {} blank = (await mainLen()) < 120; }
  // Open any requested popups/modals so they're IN the shot. Try button-by-name
  // first (accessible), then any element by visible text. Report per click so a
  // missing button is loud, not silent.
  const clickReport = [];
  for (const label of clicks) {
    let ok = false;
    try {
      const byRole = page.getByRole('button', { name: label, exact: false }).first();
      if (await byRole.count()) { await byRole.click({ timeout: 4000 }); ok = true; }
    } catch {}
    if (!ok) {
      try {
        const byText = page.getByText(label, { exact: false }).first();
        if (await byText.count()) { await byText.click({ timeout: 4000 }); ok = true; }
      } catch {}
    }
    clickReport.push(`${ok ? 'clicked' : 'NOT-FOUND'}:"${label}"`);
    await page.waitForTimeout(1200); // let the modal mount + animate in
  }
  await page.screenshot({ path: out, fullPage: true });
  console.log(`SHOT OK -> ${out} | url ${page.url()} | width ${width} | pageerrors ${errs.length}${clicks.length ? ' | clicks ' + clickReport.join(' ') : ''}${blank ? ' | WARN: content pane looks BLANK (page may need session-auth or a data call failed)' : ''}`);
} finally {
  await b.close();
}
