/**
 * qc.mjs — the Quality Controller's full-battery check on one omni page.
 *
 * The read-only /qa view lets a person LOOK. This is what the QC "knows how to
 * do" — it opens a page through that same locked read-only session and runs, in
 * one pass, the six checks that map to bug classes we have actually shipped:
 *
 *   1. RENDER      — load both laptop widths, screenshot each (visual/layout).
 *   2. JS ERRORS   — capture page errors + console errors the code review is blind to.
 *   3. BROKEN DATA — capture every API call that came back 4xx/5xx.
 *   4. ACCESS/USE  — axe-core (wcag2a/2aa + best-practice): invisible buttons,
 *                    white-on-white text, low contrast, unlabelled controls —
 *                    the "I can't see / can't find the button" class Charmaine
 *                    and Bharath kept finding that the console sweeps could not.
 *   5. SPEED       — time to first data + time to content; flag the ~10s-class
 *                    stalls (the Microsoft-check bug, 2026-07-29).
 *   6. READ-ONLY   — prove a write is refused, so the QC session itself is safe.
 *
 * Auth: the read-only QA session (OMNI_TOKEN or ~/.omni-qa-token), refreshed by
 * qc.sh. Never writes; the server refuses it on anything but a read.
 *
 * Usage:
 *   node qc.mjs "/payroll/payslips"
 *   node qc.mjs "/hris/leave" --click "Team Leave Report"
 * Writes qc_<route>_<width>.png screenshots + qc-report.json, and prints a
 * plain-English summary ranked worst-first.
 */
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import { readFileSync, writeFileSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'

const BASE = process.env.OMNI_BASE || process.env.OMNI_URL || 'https://omni.alphadirect.co.bw'

// Windows/Git Bash rewrites a leading "/" argument into "C:/Program Files/Git/..."
// before node ever sees it, which sent the first run to a nonsense hostname.
// Same fix lib.mjs already carries for the eyes-on tools. (No-op on the Mac.)
const unmangle = p => {
  const m = /^[A-Za-z]:[\\/].*?[\\/]Git[\\/](.*)$/.exec(p)
  return m ? '/' + m[1].replace(/\\/g, '/') : p
}

const route = unmangle(process.argv[2] || '')
if (!route || route.startsWith('--')) {
  console.error('usage: node qc.mjs "/route" [--click "Button"]...')
  process.exit(2)
}
const clicks = process.argv.slice(3).reduce((a, x, i, arr) => {
  if (x === '--click' && arr[i + 1]) a.push(arr[i + 1]); return a
}, [])

let token = process.env.OMNI_TOKEN
if (!token) { try { token = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim() } catch {} }
if (!token) { try { token = readFileSync(join(homedir(), '.omni-e2e-token'), 'utf8').trim() } catch {} }
if (!token) { console.error('NO_TOKEN: run qc.sh (or set OMNI_TOKEN / ~/.omni-qa-token)'); process.exit(2) }

const SAFE = route.replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'root'
const SLOW_MS = 4000          // "first data" later than this = a stall worth naming
const CONTENT_SLOW_MS = 8000  // content on screen later than this = the ~10s class

// Strip the CFO's global "task needs your action" popup so it doesn't hide the page.
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

const report = { route, base: BASE, checks: {}, findings: [] }
const add = (severity, check, msg) => report.findings.push({ severity, check, msg })

const b = await chromium.launch()

// ── 1 render + 2 JS errors + 3 broken data + 5 speed, at the sidebar-overlap width ──
{
  const ctx = await b.newContext({ viewport: { width: 1120, height: 900 }, deviceScaleFactor: 2 })
  await ctx.addInitScript(t => {
    localStorage.setItem('alpha_token', t)
    localStorage.setItem('alpha_qa_readonly', '1')
    localStorage.setItem('alpha_theme', 'professional')
  }, token)
  const page = await ctx.newPage()
  const jsErrors = []
  const consoleErrors = []
  const badApi = []
  page.on('pageerror', e => jsErrors.push(String(e).slice(0, 200)))
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)) })
  const t0 = Date.now()
  let firstApi = null
  page.on('response', r => {
    const u = r.url()
    if (!u.includes('/api/')) return
    if (firstApi === null) firstApi = Date.now() - t0
    if (r.status() >= 400) badApi.push(`${r.status()} ${u.split('/api/v1')[1]?.slice(0, 60) || u.slice(0, 60)}`)
  })

  await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  if (/\/login|\/signin|microsoftonline|\/qa$/i.test(page.url())) {
    console.error('AUTH_FAILED: bounced to sign-in — token dead. Run qc.sh to refresh.')
    process.exit(3)
  }
  // Wait for real content (not a spinner), up to 40s, and time it.
  //
  // This used to be `txt.length > 500`, which asked the wrong question: it
  // measured how MUCH text a page had, not whether it had finished loading. A
  // page that legitimately renders an empty state — /tasks for someone with no
  // tasks is about 230 characters — never crossed the bar and got reported as
  // a HIGH "stuck on a spinner" defect, with a screenshot plainly showing the
  // page rendered correctly. Two full QC runs filed it before anyone read the
  // photo (2026-09-11). A harness that cries wolf on a working screen is worse
  // than no harness: it trains you to skim past its findings.
  //
  // Now: a page is loaded when it is showing NO spinner/skeleton and has some
  // text. That catches a genuine hang (the spinner is still there) without
  // punishing a thin-but-correct page.
  let contentMs = null
  for (let i = 0; i < 80; i++) {
    await page.waitForTimeout(500)
    const state = await page.evaluate(() => {
      const root = document.querySelector('main') || document.body
      const txt = (root.innerText || '').trim()
      const visible = (el) => {
        const r = el.getBoundingClientRect()
        return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'
      }
      const busy = [...root.querySelectorAll(
        '.animate-spin,[role="status"],[aria-busy="true"],.skeleton,[class*="skeleton"]',
      )].some(visible)
      return { txt, busy }
    })
    const stillLoading = state.busy || /Loading|Loading…$/.test(state.txt.slice(-40))
    if (!stillLoading && state.txt.length > 40) { contentMs = Date.now() - t0; break }
  }
  await stripPopup(page)
  await page.waitForTimeout(1500)

  // requested pop-ups
  const clickReport = []
  for (const label of clicks) {
    let ok = false
    try { const el = page.getByRole('button', { name: label }); if (await el.count()) { await el.first().click({ timeout: 4000 }); ok = true } } catch {}
    if (!ok) { try { const el = page.getByText(label, { exact: false }); if (await el.count()) { await el.first().click({ timeout: 4000 }); ok = true } } catch {} }
    clickReport.push(`${ok ? 'opened' : 'NOT-FOUND'}:"${label}"`)
    if (!ok) add('high', 'control', `control not found / not clickable: "${label}"`)
    await page.waitForTimeout(1200)
  }

  await page.screenshot({ path: `qc_${SAFE}_1120.png`, fullPage: false })

  // ── 4 accessibility (axe) ──
  let axe = { violations: [] }
  try {
    axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'best-practice']).analyze()
  } catch (e) { add('info', 'axe', `axe could not run: ${String(e).slice(0, 80)}`) }
  const contrast = axe.violations.filter(v => v.id === 'color-contrast')
  const nameless = axe.violations.filter(v => ['button-name', 'link-name', 'input-button-name', 'select-name', 'label'].includes(v.id))
  const nContrast = contrast.reduce((s, v) => s + v.nodes.length, 0)
  const nNameless = nameless.reduce((s, v) => s + v.nodes.length, 0)

  report.checks.render = { width1120: `qc_${SAFE}_1120.png`, clicks: clickReport }
  report.checks.jsErrors = jsErrors
  report.checks.consoleErrors = consoleErrors.slice(0, 20)
  report.checks.badApi = badApi
  report.checks.speed = { firstApiMs: firstApi, contentMs }
  report.checks.axe = {
    total: axe.violations.reduce((s, v) => s + v.nodes.length, 0),
    contrast: nContrast, namelessControls: nNameless,
    rules: axe.violations.map(v => `${v.id}×${v.nodes.length}`),
  }

  if (jsErrors.length) add('high', 'js', `${jsErrors.length} JavaScript error(s) on load — e.g. ${jsErrors[0]}`)
  if (badApi.length) add('high', 'data', `${badApi.length} data request(s) failed — ${[...new Set(badApi)].slice(0, 4).join(', ')}`)
  if (nNameless) add('high', 'access', `${nNameless} control(s) with no name — invisible/unusable button or field`)
  if (nContrast) add('medium', 'access', `${nContrast} low-contrast / hard-to-read element(s)`)
  if (contentMs === null) add('high', 'render', 'still showing a spinner/skeleton after 40s — READ the screenshot before filing this')
  else if (contentMs > CONTENT_SLOW_MS) add('high', 'speed', `slow: content took ${(contentMs / 1000).toFixed(1)}s to appear`)
  else if (firstApi && firstApi > SLOW_MS) add('medium', 'speed', `slow start: first data request only at ${(firstApi / 1000).toFixed(1)}s`)

  await ctx.close()
}

// ── 1 render at 1280 (a second width catches width-only layout breaks) ──
{
  const ctx = await b.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 })
  await ctx.addInitScript(t => {
    localStorage.setItem('alpha_token', t)
    localStorage.setItem('alpha_qa_readonly', '1')
    localStorage.setItem('alpha_theme', 'professional')
  }, token)
  const page = await ctx.newPage()
  await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {})
  await page.waitForTimeout(8000)
  await stripPopup(page)
  await page.waitForTimeout(1200)
  await page.screenshot({ path: `qc_${SAFE}_1280.png`, fullPage: false })
  report.checks.render.width1280 = `qc_${SAFE}_1280.png`
  await ctx.close()
}

// ── 6 read-only safety: a write MUST be refused ──
// Run the write from a real omni page so the request is same-origin (a blank
// page makes the browser block it cross-origin before it reaches the server,
// which looks like a failure but proves nothing).
{
  const ctx = await b.newContext()
  const page = await ctx.newPage()
  await page.goto(`${BASE}/qa`, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {})
  const res = await page.evaluate(async (tok) => {
    try {
      const r = await fetch('/api/v1/companies/', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Token ${tok}` },
        body: JSON.stringify({ name: 'QC self-test — must be refused' }),
      })
      return r.status
    } catch (e) { return 'neterror:' + String(e).slice(0, 40) }
  }, token)
  const refused = res === 401 || res === 403
  report.checks.readOnly = { writeStatus: res, safe: refused }
  if (!refused) {
    // A 2xx is a real breach; a network error means "couldn't prove it", not "unsafe".
    if (typeof res === 'number' && res >= 200 && res < 300)
      add('critical', 'safety', `read-only session ACCEPTED a write (status ${res}) — NOT safe`)
    else
      add('info', 'safety', `could not confirm the write was refused (${res}) — re-run; not treated as a breach`)
  }
  await ctx.close()
}

await b.close()

// ── verdict ──
const RANK = { critical: 0, high: 1, medium: 2, info: 3 }
report.findings.sort((a, c) => RANK[a.severity] - RANK[c.severity])
writeFileSync('qc-report.json', JSON.stringify(report, null, 2))

const worst = report.findings[0]?.severity
report.verdict = report.findings.some(f => f.severity === 'critical' || f.severity === 'high') ? 'PROBLEMS'
  : report.findings.length ? 'MINOR' : 'CLEAN'

console.log(`\n===== QC: ${route} =====`)
console.log(`verdict: ${report.verdict}`)
const sp = report.checks.speed
console.log(`speed  : first data ${sp.firstApiMs ?? '-'}ms · content ${sp.contentMs ?? 'never'}${sp.contentMs ? 'ms' : ''}`)
console.log(`safety : write → ${report.checks.readOnly.writeStatus} (${report.checks.readOnly.safe ? 'refused, good' : 'ACCEPTED — BAD'})`)
console.log(`shots  : qc_${SAFE}_1120.png · qc_${SAFE}_1280.png  (READ them)`)
if (!report.findings.length) console.log('findings: none — page renders, loads fast, no errors, controls named, write refused.')
else {
  console.log('findings (worst first):')
  for (const f of report.findings) console.log(`  [${f.severity.toUpperCase()}] ${f.check}: ${f.msg}`)
}
console.log('full report: qc-report.json\n')
process.exit(report.verdict === 'PROBLEMS' ? 1 : 0)
