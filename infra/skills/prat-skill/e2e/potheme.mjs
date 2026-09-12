import { chromium } from 'playwright'
import { readFileSync } from 'fs'; import { homedir } from 'os'; import { join } from 'path'
const tok = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim()
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } })
await ctx.addInitScript(t => localStorage.setItem('alpha_token', t), tok)
const p = await ctx.newPage()
await p.goto('https://omni.alphadirect.co.bw/purchase-orders', { waitUntil: 'networkidle' })
await p.waitForTimeout(2500)
const out = await p.evaluate(() => {
  const t = document.querySelector('table'); if (!t) return 'no table'
  const pick = el => { const c = getComputedStyle(el); return { tag: el.tagName, cls: (el.className||'').toString().slice(0,120), bg: c.backgroundColor, color: c.color } }
  const res = { table: pick(t) }
  const thead = t.querySelector('thead'); if (thead) res.thead = pick(thead)
  const tb = t.querySelector('tbody'); if (tb) res.tbody = pick(tb)
  const tr = t.querySelector('tbody tr'); if (tr) res.tr = pick(tr)
  const td = t.querySelector('tbody td'); if (td) res.td = pick(td)
  // walk ancestors for the painter
  res.anc = []
  let n = t.parentElement
  for (let i=0;i<5 && n;i++){ res.anc.push(pick(n)); n = n.parentElement }
  return res
})
console.log(JSON.stringify(out, null, 1))
await b.close()
