/**
 * QC battery for Graphite V2 — the same checks qc.mjs runs against omni, but
 * pointed at a Graphite build and using Graphite's own sign-in token.
 *
 * Why a sibling and not a flag on qc.mjs: qc.mjs injects omni's `alpha_token`
 * and proves a write is refused via omni's read-only QA identity. Graphite
 * authenticates with a Sanctum bearer in `sanctum_token` and has no equivalent
 * read-only identity, so checks 1-5 port across and check 6 does not.
 *
 * Checks: 1 render (1120 + 1280) · 2 JavaScript errors · 3 failed data calls
 *         4 accessibility (axe-core) · 5 speed
 *
 * Usage:
 *   GV2_BASE=http://localhost:3000 GV2_TOKEN=xxx node qc-graphite.mjs "/claims"
 *   ...optionally --click "Major Claims" to exercise a control first.
 *
 * Exit: 0 CLEAN/MINOR · 1 PROBLEMS · 3 bounced to sign-in.
 */
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import fs from 'node:fs'

// Git Bash rewrites a leading "/" into "C:/Program Files/Git/..." — same trap
// lib.mjs already guards against for the eyes-on tools. Reuse its regex rather
// than rolling another one; the naive version splits on the wrong slash and
// turns "/claims" into "/Git/claims".
import { unmangle } from './lib.mjs'

const argv = process.argv.slice(2)
const clicks = []
const routes = []
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--click') { clicks.push(argv[++i]); continue }
  routes.push(unmangle(argv[i]))
}
const route = routes[0] || '/claims'

const BASE = process.env.GV2_BASE || 'http://localhost:3000'
const TOKEN = process.env.GV2_TOKEN || ''

const report = { route, base: BASE, checks: {}, findings: [] }
const add = (severity, check, msg) => report.findings.push({ severity, check, msg })

const browser = await chromium.launch()

const seed = (t) => {
  localStorage.setItem('sanctum_token', t)
  localStorage.setItem('user', JSON.stringify({
    id: 1, firstName: 'Quality', lastName: 'Check',
    name: 'Quality Check', email: 'omni@alphadirect.co.bw',
  }))
  localStorage.setItem('user_permissions', JSON.stringify(['*']))
  localStorage.setItem('user_roles', JSON.stringify(['claims-team']))
}

// ── 1 render + 2 JS errors + 3 failed data calls + 5 speed ──
{
  const ctx = await browser.newContext({ viewport: { width: 1120, height: 900 }, deviceScaleFactor: 2 })
  await ctx.addInitScript(seed, TOKEN)
  const page = await ctx.newPage()

  const jsErrors = [], consoleErrors = [], badApi = []
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
  if (/\/login|\/signin|microsoftonline/i.test(page.url())) {
    console.error('AUTH_FAILED: bounced to sign-in — GV2_TOKEN missing or dead.')
    process.exit(3)
  }

  let contentMs = null
  for (let i = 0; i < 80; i++) {
    await page.waitForTimeout(500)
    const txt = await page.evaluate(() => ((document.querySelector('main') || document.body).innerText || '').trim())
    if (txt.length > 300 && !/Loading|Loading…$/.test(txt.slice(-40))) { contentMs = Date.now() - t0; break }
  }
  await page.waitForTimeout(1200)

  const clickReport = []
  for (const label of clicks) {
    let ok = false
    try {
      const el = page.getByRole('button', { name: label })
      if (await el.count()) { await el.first().click({ timeout: 4000 }); ok = true }
    } catch {}
    if (!ok) {
      try {
        const el = page.getByText(label, { exact: false })
        if (await el.count()) { await el.first().click({ timeout: 4000 }); ok = true }
      } catch {}
    }
    clickReport.push(`${ok ? 'opened' : 'NOT-FOUND'}:"${label}"`)
    if (ok) await page.waitForTimeout(1500)
  }
  report.checks.clicks = clickReport

  await page.screenshot({ path: 'qc-graphite-1120.png', fullPage: true })

  // ── 4 accessibility ──
  let axe = { violations: [] }
  try {
    axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'best-practice']).analyze()
  } catch (e) { add('info', 'axe', `axe could not run: ${String(e).slice(0, 80)}`) }

  const contrast = axe.violations.filter(v => v.id === 'color-contrast')
  const nameless = axe.violations.filter(v =>
    ['button-name', 'link-name', 'input-button-name', 'select-name', 'label'].includes(v.id))

  // A blank render is a failure even when nothing errored.
  const bodyLen = (await page.evaluate(() => (document.body.innerText || '').trim().length))
  if (bodyLen < 200) add('serious', 'render', `page is close to empty (${bodyLen} chars of text)`)

  for (const e of jsErrors) add('serious', 'js', e)
  for (const e of consoleErrors) add('minor', 'console', e)
  for (const a of badApi) add('serious', 'data', `failed data call: ${a}`)
  // Name the offending elements — a bare count isn't actionable.
  const targets = (v) => v.nodes.map(n => (n.target || []).join(' ')).slice(0, 6).join(' | ')
  for (const v of nameless) add('serious', 'a11y', `${v.id}: ${v.nodes.length} control(s) with no accessible name -> ${targets(v)}`)
  for (const v of contrast) add('minor', 'a11y', `color-contrast: ${v.nodes.length} element(s) below the ratio -> ${targets(v)}`)

  report.checks.render = { bodyChars: bodyLen, shot: 'qc-graphite-1120.png' }
  report.checks.speed = { firstDataMs: firstApi, contentMs }
  report.checks.a11y = {
    violations: axe.violations.length,
    namelessControls: nameless.reduce((n, v) => n + v.nodes.length, 0),
    contrastNodes: contrast.reduce((n, v) => n + v.nodes.length, 0),
  }
  if (contentMs === null) add('serious', 'speed', 'content never settled within 40s')
  else if (contentMs > 8000) add('minor', 'speed', `content took ${contentMs}ms to settle`)

  await ctx.close()
}

// second width — layout only
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 })
  await ctx.addInitScript(seed, TOKEN)
  const page = await ctx.newPage()
  await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(3500)
  for (const label of clicks) {
    try {
      const el = page.getByRole('button', { name: label })
      if (await el.count()) { await el.first().click({ timeout: 4000 }); await page.waitForTimeout(1200) }
    } catch {}
  }
  await page.screenshot({ path: 'qc-graphite-1280.png', fullPage: true })
  // The page body must never scroll sideways, whatever the table does inside it.
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth)
  if (overflow > 4) add('minor', 'layout', `page scrolls sideways by ${overflow}px at 1280`)
  report.checks.render1280 = { shot: 'qc-graphite-1280.png', horizontalOverflow: overflow }
  await ctx.close()
}

await browser.close()

const serious = report.findings.filter(f => f.severity === 'serious').length
const minor = report.findings.filter(f => f.severity === 'minor').length
report.verdict = serious ? 'PROBLEMS' : minor ? 'MINOR' : 'CLEAN'

fs.writeFileSync('qc-graphite-report.json', JSON.stringify(report, null, 2))

console.log(`\n  QC ${report.verdict}  —  ${BASE}${route}`)
console.log(`  render     ${report.checks.render.bodyChars} chars · shots qc-graphite-1120.png / qc-graphite-1280.png`)
console.log(`  speed      first data ${report.checks.speed.firstDataMs}ms · content ${report.checks.speed.contentMs}ms`)
console.log(`  a11y       ${report.checks.a11y.violations} violation type(s) · ${report.checks.a11y.namelessControls} unnamed control(s) · ${report.checks.a11y.contrastNodes} low-contrast node(s)`)
if (report.checks.clicks.length) console.log(`  clicks     ${report.checks.clicks.join(' · ')}`)
console.log(`  layout     sideways overflow at 1280: ${report.checks.render1280.horizontalOverflow}px`)
if (report.findings.length) {
  console.log('')
  for (const f of report.findings) console.log(`  [${f.severity}] ${f.check}: ${f.msg}`)
}
console.log('')
process.exit(serious ? 1 : 0)
