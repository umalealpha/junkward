// Shared helpers for the omni "eyes-on" screenshot toolkit.
// Everything else in this folder builds on these four things:
//   loadSession()  - reuse a saved login instead of typing a password
//   openPage()     - a browser tab at a laptop width, already logged in
//   shoot()        - full-page PNG of whatever is on screen
//   contactSheet() - glue several PNGs into one picture (no extra libraries)

import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

export const HERE = path.dirname(fileURLToPath(import.meta.url));
export const SESSION_DIR = path.join(HERE, 'sessions');
export const SHOT_DIR = path.join(HERE, 'shots');

export const BASE = (process.env.OMNI_BASE || 'https://omni.alphadirect.co.bw').replace(/\/$/, '');
export const WIDTHS = [1120, 1280];
export const HEIGHT = 820;

export const ROLES = {
  admin: { file: 'admin.json', label: 'admin (CFO)' },
  staff: { file: 'staff.json', label: 'staff (finance manager)' },
};

export function sessionPath(role) {
  const r = ROLES[role];
  if (!r) throw new Error(`Unknown role "${role}". Use admin or staff.`);
  return path.join(SESSION_DIR, r.file);
}

// A saved session is { storageState, sessionStorage }.
// storageState covers cookies + localStorage; sessionStorage has to be
// re-injected by hand because Playwright does not carry it.
export function loadSession(role) {
  const p = sessionPath(role);
  if (!fs.existsSync(p)) {
    throw new Error(
      `No saved login for "${role}".\n` +
      `Run:  node omni-login.mjs ${role}\n` +
      `(a browser opens, you sign in once, and the session is saved to ${p})`
    );
  }
  const raw = JSON.parse(fs.readFileSync(p, 'utf8'));
  const ageDays = (Date.now() - new Date(raw.savedAt || 0).getTime()) / 86400000;
  return { ...raw, ageDays };
}

// Use Playwright's own Chromium if it has been downloaded; otherwise fall back
// to the Google Chrome already installed on this PC, so the toolkit works even
// when the browser download is blocked.
export async function openBrowser(opts = {}) {
  try {
    return await chromium.launch(opts);
  } catch (err) {
    // Missing download, locked by antivirus, or (headed mode) Chromium refusing
    // to spawn a window on this PC - "spawn UNKNOWN".
    if (!/Executable doesn't exist|please run|install|EBUSY|EACCES|EPERM|spawn (UNKNOWN|ENOENT)/i.test(String(err.message))) throw err;
    return await chromium.launch({ ...opts, channel: 'chrome' });
  }
}

// A logged-in tab on an already-running browser. Use this when shooting many
// pages in one go; openPage() below is the one-shot convenience wrapper.
export async function newRolePage(browser, { role, width = WIDTHS[0], height = HEIGHT, anonymous = false }) {
  let contextOpts = { viewport: { width, height }, deviceScaleFactor: 2 };
  let saved = null;

  if (!anonymous) {
    saved = loadSession(role);
    contextOpts.storageState = saved.storageState;
  }

  const context = await browser.newContext(contextOpts);

  if (saved?.sessionStorage) {
    const entries = saved.sessionStorage;
    await context.addInitScript((data) => {
      for (const [k, v] of Object.entries(data)) {
        try { window.sessionStorage.setItem(k, v); } catch { /* ignore */ }
      }
    }, entries);
  }

  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => consoleErrors.push(String(e)));

  return { context, page, consoleErrors, sessionAgeDays: saved?.ageDays };
}

export async function openPage(opts) {
  const browser = await openBrowser();
  return { browser, ...(await newRolePage(browser, opts)) };
}

// Git Bash rewrites a leading "/" into "C:/Program Files/Git/..." before Node
// ever sees it. Undo that so "/dashboard" means /dashboard everywhere.
export function unmangle(p) {
  const m = /^[A-Za-z]:[\\/].*?[\\/]Git[\\/](.*)$/.exec(p);
  return m ? '/' + m[1].replace(/\\/g, '/') : p;
}

export async function gotoPath(page, rawPath) {
  const urlOrPath = unmangle(rawPath);
  const url = /^https?:\/\//.test(urlOrPath) ? urlOrPath : BASE + (urlOrPath.startsWith('/') ? '' : '/') + urlOrPath;
  const res = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await settle(page);
  return { url, status: res ? res.status() : null };
}

// Wait for the page to stop moving: network quiet, then a beat for animations.
export async function settle(page) {
  try { await page.waitForLoadState('networkidle', { timeout: 20000 }); } catch { /* slow poller is fine */ }
  // Don't photograph a half-loaded screen. A page can go network-idle while a
  // slow call is still in flight, which once made a working fix look broken.
  try {
    await page.waitForFunction(
      () => !/\b(loading|checking access|please wait)\b/i.test(document.body?.innerText || ''),
      null, { timeout: 8000 },
    );
  } catch { /* genuinely stuck on "loading" - that is itself the finding */ }
  await page.waitForTimeout(900);
}

export async function shoot(page, outPath, { fullPage = true } = {}) {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await page.screenshot({ path: outPath, fullPage });
  return outPath;
}

// Click something by its visible text, then wait for whatever it opened.
export async function clickByText(page, text) {
  const target = page
    .getByRole('button', { name: text, exact: false })
    .or(page.getByRole('link', { name: text, exact: false }))
    .or(page.getByText(text, { exact: false }))
    .first();
  await target.waitFor({ state: 'visible', timeout: 15000 });
  await target.click();
  await settle(page);
}

// Is this screen actually usable, or is it blank / spinning / blocked?
export async function verdict(page, status, consoleErrors) {
  const body = (await page.locator('body').innerText().catch(() => '')) || '';
  const text = body.replace(/\s+/g, ' ').trim();
  const low = text.toLowerCase();

  if (status && status >= 500) return { state: 'BROKEN', why: `server error ${status}` };
  if (status === 404) return { state: 'BROKEN', why: 'page not found (404)' };
  if (/access restricted|not authorised|not authorized|permission denied|forbidden|you do not have/.test(low))
    return { state: 'BLOCKED', why: 'permission wall' };
  if (/something went wrong|application error|unhandled|failed to fetch/.test(low))
    return { state: 'BROKEN', why: 'error message on screen' };
  if (text.length < 40) {
    const spinner = await page.locator('[class*="spin"], [class*="load"], [role="progressbar"]').count().catch(() => 0);
    return { state: spinner ? 'SPINNING' : 'BLANK', why: spinner ? 'still loading' : 'no content rendered' };
  }
  if (consoleErrors?.length) return { state: 'OK*', why: `${consoleErrors.length} console error(s)` };
  return { state: 'OK', why: '' };
}

// OK* means "it worked, but the browser logged console errors" - worth knowing,
// not a broken screen. Anything else needs a human to look.
export const isProblem = (state) => !['OK', 'OK*'].includes(state);

// Stitch PNGs into one picture by rendering them in a plain HTML page and
// screenshotting that. Keeps the toolkit dependency-free.
export async function contactSheet(items, outPath, { title = '', columns = 2, width = 1500 } = {}) {
  const cells = items.map((it) => {
    const b64 = fs.readFileSync(it.file).toString('base64');
    const badge = it.state ? `<span class="badge ${it.state.replace('*', 'star')}">${it.state}</span>` : '';
    return `<figure><figcaption>${badge}<b>${escapeHtml(it.caption || '')}</b>${
      it.note ? `<span class="note">${escapeHtml(it.note)}</span>` : ''
    }</figcaption><img src="data:image/png;base64,${b64}"></figure>`;
  }).join('\n');

  const html = `<!doctype html><meta charset="utf-8"><style>
    body{margin:0;padding:28px;background:#0D1B2A;font-family:"Book Antiqua",Georgia,serif;color:#fff}
    h1{font-size:22px;margin:0 0 20px;color:#F47C20}
    .grid{display:grid;grid-template-columns:repeat(${columns},1fr);gap:22px;align-items:start}
    figure{margin:0;background:#fff;border-radius:8px;overflow:hidden;border:2px solid #1D3270}
    figcaption{padding:10px 12px;background:#1D3270;font-size:14px;display:flex;align-items:center;gap:10px}
    .note{opacity:.75;font-size:12px}
    img{display:block;width:100%;height:auto}
    .badge{font-size:11px;font-weight:bold;padding:2px 8px;border-radius:10px;background:#2e7d32}
    .BROKEN,.BLANK{background:#c62828}.BLOCKED{background:#ef6c00}.SPINNING{background:#6a1b9a}.OKstar{background:#f9a825;color:#000}
  </style><body>${title ? `<h1>${escapeHtml(title)}</h1>` : ''}<div class="grid">${cells}</div></body>`;

  const browser = await openBrowser();
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  await page.setContent(html, { waitUntil: 'load' });
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await page.screenshot({ path: outPath, fullPage: true });
  await browser.close();
  return outPath;
}

export function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// Split "path out.png --as staff --width 1120" into { positional, flags }.
export function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) { flags[a.slice(2)] = argv[i + 1]; i++; }
    else positional.push(a);
  }
  return { positional, flags };
}

export function slug(s) {
  return String(s).replace(/^https?:\/\/[^/]+/, '').replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'home';
}

export function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}
