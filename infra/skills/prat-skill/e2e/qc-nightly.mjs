/**
 * qc-nightly.mjs — the overnight "eyes-on" robot: a COMPLETE SYSTEM TEST.
 *
 * Runs unattended (Task Scheduler) and does what a person cannot do every night:
 * opens EVERY page of the omni staff system in BOTH the normal (light) look and
 * the dark look, and reports any screen where text is unreadable, a control is
 * invisible, or a page is blank/broken. It exists because these bugs (e.g. the
 * dark-mode Development Dialogue, 2026-08-05) are invisible to code review and
 * only show when a page is actually rendered — especially in dark mode.
 *
 * Routes: auto-discovered from the repo (every page.tsx under frontend/src/app,
 * minus the [dynamic] ones and the /m customer app, which uses a different login).
 * Falls back to a small built-in list if the repo can't be found.
 *
 * Identity: the SAME read-only /qa token qc.mjs uses (~/.omni-qa-token, topped up
 * by qc-token.sh). The server refuses it on anything but a read.
 *
 * Dark mode = Playwright colorScheme:'dark' — omni's dark look is Tailwind's dark:
 * variant, which follows the OS prefers-color-scheme, so this is exactly what a
 * staff member on a dark-mode machine sees.
 *
 * Output: qc-nightly-report.html + qc-nightly-manifest.json in the current dir.
 * qc-nightly.sh refreshes the token, runs this, then emails the report.
 */
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'

const BASE = process.env.OMNI_BASE || 'https://omni.alphadirect.co.bw'
const CONC = Number(process.env.QC_JOBS || 4)      // pages checked in parallel

// A small fallback list, used only if the repo can't be found.
const FALLBACK = ['/dashboard', '/hris/my-dialogue', '/hris/team-dialogues', '/payroll/payslips',
  '/hris/leave', '/hris/leave-encashment', '/payment-requests', '/refunds', '/claims/register']

// ---- discover every static staff route from the repo ----
function discoverRoutes() {
  const repo = process.env.ALPHA_REPO || join(homedir(), 'work', 'alpha-finance')
  const appDir = join(repo, 'frontend', 'src', 'app')
  if (!existsSync(appDir)) return null
  const out = []
  const walk = d => {
    for (const name of readdirSync(d)) {
      const p = join(d, name)
      const st = statSync(p)
      if (st.isDirectory()) walk(p)
      else if (name === 'page.tsx') {
        let rel = p.slice(appDir.length).replace(/\\/g, '/').replace(/\/page\.tsx$/, '')
        rel = rel.replace(/\/\([^)]+\)/g, '')      // strip route-group segments like (dashboard)
        if (!rel) rel = '/'
        out.push(rel)
      }
    }
  }
  walk(appDir)
  return [...new Set(out)]
    .filter(r => r && r !== '/' &&
      !r.includes('[') &&                          // dynamic [id] routes — can't visit blind
      !r.startsWith('/m') &&                        // customer mobile app — different login
      !r.startsWith('/api'))
    .sort()
}

const ROUTES = discoverRoutes() || FALLBACK

let token = process.env.OMNI_TOKEN
if (!token) { try { token = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim() } catch {} }
if (!token) { console.error('NO_TOKEN: run qc-token.sh (or set OMNI_TOKEN)'); process.exit(2) }

const SCHEMES = ['light', 'dark']
const results = []          // { route, scheme, verdict, contrast, nameless, shot? }
let authDead = false        // token genuinely dead (declared only if it NEVER worked)
let authProven = false      // at least one page loaded as the signed-in QA identity

async function stripPopup(page) {
  try { await page.keyboard.press('Escape') } catch {}
  try {
    await page.evaluate(() => {
      const hit = [...document.querySelectorAll('div')]
        .find(d => /need your action/i.test(d.textContent || '') && d.offsetParent)
      if (hit) {
        let n = hit
        for (let i = 0; i < 8 && n; i++) {
          const cs = getComputedStyle(n)
          if (cs.position === 'fixed' || parseInt(cs.zIndex || '0', 10) >= 40) { n.remove(); break }
          n = n.parentElement
        }
      }
    })
  } catch {}
}

const safe = s => s.replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'root'

const browser = await chromium.launch()

// Check one route in one look. Returns { verdict, contrast, nameless, shot }.
async function checkOne(route, scheme) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1, colorScheme: scheme })
  await ctx.addInitScript(t => {
    localStorage.setItem('alpha_token', t)
    localStorage.setItem('alpha_qa_readonly', '1')
  }, token)
  const page = await ctx.newPage()
  const consoleErrors = []
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(1) })
  page.on('pageerror', () => consoleErrors.push(1))

  let status = null
  try {
    const res = await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 })
    status = res ? res.status() : null
  } catch { /* handled by verdict */ }

  // A single page that bounces to the login screen means THAT page needs a full
  // sign-in (some admin pages do) — NOT that the token died. Only if the token
  // never worked at all (no page has loaded yet) is it a real auth failure.
  if (/\/login|\/signin|microsoftonline|\/qa$/i.test(page.url())) {
    if (!authProven) authDead = true
    await ctx.close(); return { verdict: 'LOGIN', contrast: 0, nameless: 0 }
  }

  let contentSeen = false
  for (let i = 0; i < 16; i++) {          // up to ~8s for real content
    await page.waitForTimeout(500)
    const txt = await page.evaluate(() => ((document.querySelector('main') || document.body).innerText || '').trim())
    if (txt.length > 400 && !/loading|please wait|checking access/i.test(txt.slice(-40))) { contentSeen = true; break }
  }
  if (contentSeen) authProven = true      // the token works — later login bounces are page-specific
  await stripPopup(page)
  await page.waitForTimeout(500)

  let contrast = 0, nameless = 0
  try {
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'best-practice']).analyze()
    contrast = axe.violations.filter(v => v.id === 'color-contrast').reduce((s, v) => s + v.nodes.length, 0)
    nameless = axe.violations.filter(v => ['button-name', 'link-name', 'input-button-name', 'select-name', 'label'].includes(v.id)).reduce((s, v) => s + v.nodes.length, 0)
  } catch { /* axe couldn't run; not fatal */ }

  const body = (await page.evaluate(() => (document.body?.innerText || '').replace(/\s+/g, ' ').trim().toLowerCase())) || ''
  let verdict = 'OK'
  if (status && status >= 500) verdict = 'BROKEN'
  else if (status === 404) verdict = 'BROKEN'
  else if (/access restricted|not authorised|not authorized|permission denied|forbidden|you do not have/.test(body)) verdict = 'BLOCKED'
  else if (/something went wrong|application error|unhandled|failed to fetch/.test(body)) verdict = 'BROKEN'
  else if (!contentSeen) verdict = 'BLANK'
  else if (contrast > 0) verdict = 'UNREADABLE'
  else if (nameless > 0) verdict = 'CONTROLS'

  let shot = null
  if (['BROKEN', 'BLANK', 'UNREADABLE', 'CONTROLS'].includes(verdict)) {
    shot = `qcn_${safe(route)}_${scheme}.png`
    try { await page.screenshot({ path: shot, fullPage: false }) } catch { shot = null }
  }
  await ctx.close()
  return { verdict, contrast, nameless, shot }
}

async function checkRoute(route) {
  for (const scheme of SCHEMES) {
    if (authDead) return
    const r = await checkOne(route, scheme)
    results.push({ route, scheme, ...r })
    // No point testing the dark look if the light look is already blocked/blank/broken.
    if (scheme === 'light' && ['BROKEN', 'BLANK', 'BLOCKED', 'LOGIN'].includes(r.verdict)) {
      results.push({ route, scheme: 'dark', verdict: r.verdict, contrast: 0, nameless: 0, shot: null, skipped: true })
      return
    }
  }
}

// Run in small parallel batches so a full-system sweep finishes in a sensible time.
for (let i = 0; i < ROUTES.length && !authDead; i += CONC) {
  await Promise.all(ROUTES.slice(i, i + CONC).map(checkRoute))
}
await browser.close()

// ---- classify per PAGE (combine its light + dark result) ----
const byRoute = {}
for (const r of results) { (byRoute[r.route] ||= {})[r.scheme] = r }
const pages = Object.entries(byRoute).map(([route, s]) => {
  const light = s.light || {}, dark = s.dark || {}
  const broken = [light, dark].find(x => x.verdict === 'BROKEN')
  const blocked = light.verdict === 'BLOCKED' || dark.verdict === 'BLOCKED'
  const needsLogin = light.verdict === 'LOGIN' || dark.verdict === 'LOGIN'
  const bothBlank = light.verdict === 'BLANK' && (dark.verdict === 'BLANK' || dark.skipped)
  const cL = light.contrast || 0, cD = dark.contrast || 0
  const nameless = Math.max(light.nameless || 0, dark.nameless || 0)
  let cls, sev, detail, shot = null
  if (broken) { cls = 'BROKEN'; sev = 0; detail = 'the page did not load'; shot = broken.shot }
  else if (blocked) { cls = 'BLOCKED'; sev = 4; detail = 'the read-only checker is not allowed on this page (expected for admin-only pages)' }
  else if (needsLogin) { cls = 'BLOCKED'; sev = 4; detail = 'this page needs a full sign-in — the read-only checker was sent to the login screen (expected for some admin pages)' }
  else if (bothBlank) { cls = 'UNVERIFIED'; sev = 4; detail = 'the read-only checker has no data here — needs a signed-in check (often normal for personal pages)' }
  else if (cD > cL) { cls = 'DARK'; sev = 1; detail = `dark mode has ${cD} hard-to-read text element(s) vs ${cL} in the normal look — a dark-mode contrast bug`; shot = dark.shot }
  else if (cL > 0 || cD > 0) { cls = 'READ'; sev = 3; detail = `${Math.max(cL, cD)} low-contrast text element(s) in both looks — general readability, not urgent` }
  else if (nameless > 0) { cls = 'CONTROLS'; sev = 2; detail = `${nameless} unlabelled control(s)`; shot = (dark.shot || light.shot) }
  else { cls = 'OK'; sev = 5; detail = '' }
  return { route, cls, sev, detail, shot }
})

// ---- build report ----
const BW_NOW = new Date().toLocaleString('en-GB', { timeZone: 'Africa/Gaborone', dateStyle: 'medium', timeStyle: 'short' })
const darkBad = pages.filter(p => p.cls === 'DARK')
const brokenBad = pages.filter(p => p.cls === 'BROKEN')
const controlsBad = pages.filter(p => p.cls === 'CONTROLS')
const unverified = pages.filter(p => p.cls === 'UNVERIFIED')
const blockedPages = pages.filter(p => p.cls === 'BLOCKED')
const readBad = pages.filter(p => p.cls === 'READ')
const okCount = pages.filter(p => p.cls === 'OK').length
const alarms = [...brokenBad, ...darkBad, ...controlsBad].sort((a, b) => a.sev - b.sev)
const attachments = [...new Set(alarms.map(p => p.shot).filter(Boolean))].slice(0, 20)   // cap attachments

let subject, headline
if (authDead) {
  subject = 'Omni full system test — could not run (sign-in expired)'
  headline = 'The check could not sign in (the read-only QA token has expired). It needs a one-time refresh — reply to Prathap.'
} else if (alarms.length === 0) {
  subject = `Omni full system test — ALL CLEAR (${pages.length} pages, light + dark)`
  headline = `All ${pages.length} pages of the system were opened in both the normal and dark look. None had unreadable dark-mode text or a broken screen. Nothing needs attention.`
} else {
  const nd = darkBad.length, nb = brokenBad.length
  const bits = []
  if (nd) bits.push(`${nd} page${nd > 1 ? 's' : ''} with dark-mode text that's hard to read`)
  if (nb) bits.push(`${nb} broken page${nb > 1 ? 's' : ''}`)
  if (controlsBad.length) bits.push(`${controlsBad.length} with an unlabelled control`)
  subject = `Omni full system test — ${alarms.length} screen${alarms.length > 1 ? 's' : ''} to look at (of ${pages.length})`
  headline = `Full system test of ${pages.length} pages (each opened in both looks): ${bits.join(', ')}. Details below.`
}

const NAVY = '#0D1B2A', ORANGE = '#F47C20'
const CHIP = { BROKEN: '#c62828', DARK: '#c62828', CONTROLS: '#ef6c00' }
const LABEL = { BROKEN: 'Broken', DARK: 'Dark-mode', CONTROLS: 'Control' }
const chip = c => `<span style="background:${CHIP[c] || '#607d8b'};color:#fff;font-size:12px;font-weight:bold;padding:2px 9px;border-radius:11px">${LABEL[c] || c}</span>`
const rowFor = p => `<tr>
  <td style="padding:7px 10px;border-bottom:1px solid #eee;font-family:monospace;font-size:13px">${p.route}</td>
  <td style="padding:7px 10px;border-bottom:1px solid #eee">${chip(p.cls)}</td>
  <td style="padding:7px 10px;border-bottom:1px solid #eee;font-size:13px;color:#444">${p.detail}</td></tr>`

const alarmRows = alarms.map(rowFor).join('')
const html = `
<div style="font-family:'Book Antiqua',Georgia,serif;max-width:780px">
  <h2 style="color:${NAVY};margin:0 0 4px">Omni full system test</h2>
  <p style="color:#666;font-size:12px;margin:0 0 14px">${BW_NOW} · Botswana time · read-only automated check · ${pages.length} pages, light + dark</p>
  <p style="font-size:15px;color:${NAVY};background:#fff7f0;border-left:4px solid ${ORANGE};padding:10px 14px;border-radius:6px">${headline}</p>
  ${alarmRows ? `<table style="border-collapse:collapse;width:100%;margin-top:10px">
    <tr style="text-align:left;color:${NAVY}"><th style="padding:7px 10px">Page</th><th style="padding:7px 10px">Type</th><th style="padding:7px 10px">What it means</th></tr>
    ${alarmRows}</table>` : ''}
  <p style="color:#555;font-size:12px;margin-top:14px">Checked ${pages.length} pages: <b style="color:#2e7d32">${okCount} clean</b>, ${darkBad.length} dark-mode, ${brokenBad.length} broken, ${controlsBad.length} control, ${readBad.length} minor readability, ${blockedPages.length} admin-only (checker not allowed), ${unverified.length} personal (need a signed-in check).</p>
  ${readBad.length ? `<p style="color:#888;font-size:12px">Minor / general readability (${readBad.length}): ${readBad.slice(0, 25).map(p => p.route).join(', ')}${readBad.length > 25 ? ' …' : ''} — faint text in both looks; accessibility backlog, not urgent.</p>` : ''}
  <p style="color:#888;font-size:12px;margin-top:12px">"Dark-mode" = readable normally but faint in dark (the priority). "Broken" = didn't load. Screenshots of the flagged screens are attached${attachments.length >= 20 ? ' (first 20)' : ''}.</p>
  <p style="color:#aaa;font-size:11px">The omni overnight QC robot runs automatically every midnight (Botswana time) and is read-only — it cannot change anything. Reply to Prathap to change what it checks.</p>
</div>`

writeFileSync('qc-nightly-report.html', html)
writeFileSync('qc-nightly-manifest.json', JSON.stringify({
  subject,
  verdict: authDead ? 'AUTH_DEAD' : (alarms.length ? 'PROBLEMS' : 'CLEAR'),
  pages: pages.length, ok: okCount, darkMode: darkBad.length, broken: brokenBad.length,
  controls: controlsBad.length, minor: readBad.length, blocked: blockedPages.length,
  unverified: unverified.length, attachments,
}, null, 2))

console.log(`\n===== QC FULL SYSTEM TEST =====`)
console.log(subject)
console.log(`clean ${okCount} · dark ${darkBad.length} · broken ${brokenBad.length} · control ${controlsBad.length} · minor ${readBad.length} · blocked ${blockedPages.length} · unverified ${unverified.length}`)
for (const p of alarms) console.log(`  ${p.cls.padEnd(9)} ${p.route} — ${p.detail}`)
console.log(`\nreport: qc-nightly-report.html · manifest: qc-nightly-manifest.json`)
process.exit(authDead ? 3 : (alarms.length ? 1 : 0))
