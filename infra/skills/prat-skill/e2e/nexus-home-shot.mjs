// nexus-home-shot.mjs — photograph the LIVE Alpha Nexus home (/m) as the App-Review
// demo member and prove the self-report tiles are gone (CFO 7-Sep-2026).
//
//   node nexus-home-shot.mjs [outPng]
//
// Login: appreview@alphadirect.co.bw + the fixed review code read from
// ~/.nexus-review-otp (never printed, never in the repo). Then:
//   * screenshot the home at phone width;
//   * assert "Log steps" / "Log a workout" are ABSENT and "Sync steps" is PRESENT;
//   * with the member's own session token, POST kind=steps and kind=fitness to the
//     activity endpoint — both must be refused (400) and the meal path must still be
//     reachable (its 400 is "take a photo", not "no longer earn").
// Exits non-zero on any failure so it can gate a deploy.
import { chromium } from 'playwright';
import fs from 'fs';
import os from 'os';
import path from 'path';

const BASE = (process.env.OMNI_BASE || 'https://omni.alphadirect.co.bw').replace(/\/$/, '');
const out = process.argv[2] || path.join(process.cwd(), 'nexus-home.png');
const otp = fs.readFileSync(path.join(os.homedir(), '.nexus-review-otp'), 'utf8').trim();
const email = 'appreview@alphadirect.co.bw';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
  userAgent: 'Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Mobile Safari/537.36' });
const fails = [];
const consoleErrors = [];
page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });

await page.goto(`${BASE}/m/login`, { waitUntil: 'networkidle' });
await page.fill('input[type="email"]', email);
await page.getByRole('button', { name: /Email me a code/ }).click();
await page.locator('input[inputmode="numeric"]').waitFor({ timeout: 20000 });
await page.fill('input[inputmode="numeric"]', otp);
await page.getByRole('button', { name: /^Sign in$/ }).click();
await page.waitForURL(u => /\/m\/?$/.test(new URL(u).pathname), { timeout: 20000 });
await page.getByText('Earn more points').waitFor({ timeout: 20000 });
await page.waitForTimeout(1500);

const body = await page.evaluate(() => document.body.innerText);
const has = (t) => body.includes(t);
if (has('Log steps')) fails.push('"Log steps" tile still on the page');
if (has('Log a workout')) fails.push('"Log a workout" tile still on the page');
if (has('How many steps today?')) fails.push('typed-steps panel still on the page');
if (!has('Sync steps')) fails.push('"Sync steps" tile missing');
if (has('Sync steps and workouts')) fails.push('tile still says "Sync steps and workouts" — v11 label must wait for the v11 app on Play');
if (!has('from your phone')) fails.push('new "from your phone" label missing (old bundle served?)');

await page.screenshot({ path: out, fullPage: true });
// The tiles sit below the fold inside the scroll container — photograph them too.
const earn = page.getByText('Earn more points');
await earn.scrollIntoViewIfNeeded();
await page.waitForTimeout(400);
const out2 = out.replace(/\.png$/i, '-earn.png');
await page.screenshot({ path: out2 });
console.log('shot   ', out2);

// Server-side proof with the member's OWN session token (the fakeable path).
const api = await page.evaluate(async () => {
  const tok = localStorage.getItem('alpha_rewards_token');
  const post = async (payload) => {
    const r = await fetch('/api/v1/rewards/customer/activity/', { method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tok}` },
      body: JSON.stringify(payload) });
    let j = {}; try { j = await r.json(); } catch {}
    return { status: r.status, detail: j.detail || '' };
  };
  return {
    steps: await post({ kind: 'steps', steps: 12000 }),
    fitness: await post({ kind: 'fitness' }),
    meal: await post({ kind: 'healthy_eating' }),
  };
});
if (api.steps.status !== 400 || !/phone/i.test(api.steps.detail)) fails.push(`typed steps not refused: ${JSON.stringify(api.steps)}`);
if (api.fitness.status !== 400 || !/phone/i.test(api.fitness.detail)) fails.push(`one-tap workout not refused: ${JSON.stringify(api.fitness)}`);
if (/and workouts/i.test(api.steps.detail + api.fitness.detail)) fails.push('server refusal message still says "Sync steps and workouts" — must match the tile until v11 is on Play');
if (api.meal.status !== 400 || !/photo/i.test(api.meal.detail)) fails.push(`meal path changed unexpectedly: ${JSON.stringify(api.meal)}`);

await browser.close();
console.log('shot   ', out);
console.log('api    ', JSON.stringify(api));
console.log('console', consoleErrors.length ? consoleErrors.slice(0, 5) : 'no errors');
if (fails.length) { console.log('VERDICT FAIL'); for (const f of fails) console.log(' -', f); process.exit(1); }
console.log('VERDICT PASS — no typed steps, no one-tap workout, Sync steps present, server refuses self-reports');
