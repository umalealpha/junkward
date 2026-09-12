/**
 * a11y-names.mjs — WHICH controls have no accessible name, and where.
 *
 * `qc.mjs` says "4 control(s) with no name". That is enough to know there is a
 * problem and useless for fixing it, because a name can be missing for five
 * different reasons (no label, a label not tied to its input, an icon-only
 * button, an empty link, a select with nothing naming it). This dumps the
 * offending elements themselves so the fix targets the real cause instead of
 * guessing at the house pattern.
 *
 * Read-only: same locked QA session as qc.mjs, no writes, no data touched.
 *
 * Usage:
 *   node a11y-names.mjs /bonu /bonu/intake /bonu/legal-bills ...
 */
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import { readFileSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'

const BASE = process.env.OMNI_BASE || 'https://omni.alphadirect.co.bw'
const unmangle = p => {
  const m = /^[A-Za-z]:[\\/].*?[\\/]Git[\\/](.*)$/.exec(p)
  return m ? '/' + m[1].replace(/\\/g, '/') : p
}
const routes = process.argv.slice(2).map(unmangle).filter(r => r && !r.startsWith('--'))
if (!routes.length) { console.error('usage: node a11y-names.mjs /bonu /bonu/intake ...'); process.exit(2) }

let token = process.env.OMNI_TOKEN
if (!token) { try { token = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim() } catch {} }
if (!token) { console.error('NO_TOKEN: run qc.sh once to mint one'); process.exit(2) }

// The axe rules that mean "a person cannot tell what this control is".
const NAME_RULES = ['button-name', 'link-name', 'input-button-name', 'select-name',
                    'label', 'aria-input-field-name', 'form-field-multiple-labels']

const b = await chromium.launch()
const totals = {}

for (const route of routes) {
  const ctx = await b.newContext({ viewport: { width: 1280, height: 1000 } })
  await ctx.addInitScript(t => {
    localStorage.setItem('alpha_token', t)
    localStorage.setItem('alpha_qa_readonly', '1')
    localStorage.setItem('alpha_theme', 'professional')
  }, token)
  const page = await ctx.newPage()
  try {
    await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    if (/\/login|\/signin|microsoftonline/i.test(page.url())) {
      console.log(`\n### ${route}\n  AUTH_FAILED — refresh the token with qc.sh`); await ctx.close(); continue
    }
    for (let i = 0; i < 60; i++) {
      await page.waitForTimeout(500)
      const txt = await page.evaluate(() => ((document.querySelector('main') || document.body).innerText || '').trim())
      if (txt.length > 400 && !/Loading|Loading…$/.test(txt.slice(-40))) break
    }
    await page.waitForTimeout(1200)

    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'best-practice']).analyze()
    const hits = axe.violations.filter(v => NAME_RULES.includes(v.id))
    const n = hits.reduce((s, v) => s + v.nodes.length, 0)
    totals[route] = n
    console.log(`\n### ${route}  — ${n} unnamed control(s)`)
    for (const v of hits) {
      console.log(`  rule ${v.id} x${v.nodes.length}`)
      for (const node of v.nodes) {
        const html = (node.html || '').replace(/\s+/g, ' ').slice(0, 190)
        console.log(`    - ${node.target?.join(' ') || ''}`)
        console.log(`      ${html}`)
      }
    }
  } catch (e) {
    console.log(`\n### ${route}\n  ERROR ${String(e).slice(0, 140)}`)
  }
  await ctx.close()
}

await b.close()
console.log('\n=== unnamed controls per screen ===')
for (const [r, n] of Object.entries(totals).sort((a, c) => c[1] - a[1])) {
  console.log(`${String(n).padStart(3)}  ${r}`)
}
const sum = Object.values(totals).reduce((a, c) => a + c, 0)
console.log(`${String(sum).padStart(3)}  TOTAL`)
