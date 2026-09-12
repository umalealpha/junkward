import { chromium } from 'playwright'
import { readFileSync } from 'fs'; import { homedir } from 'os'; import { join } from 'path'
const tok = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim()
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } })
await ctx.addInitScript(t => localStorage.setItem('alpha_token', t), tok)
const p = await ctx.newPage()
await p.goto('https://omni.alphadirect.co.bw/purchase-orders', { waitUntil: 'networkidle' })
await p.waitForTimeout(3000)
const out = await p.evaluate(() => {
  const hit = [...document.querySelectorAll('*')].find(e => /PO-CLM-2026-000437/.test(e.textContent||'') && e.children.length===0)
  if (!hit) return { err: 'row text not found', tables: document.querySelectorAll('table').length }
  const pick = el => { const c = getComputedStyle(el); return { tag: el.tagName, cls: (el.className||'').toString().slice(0,160), bg: c.backgroundColor, color: c.color } }
  const chain = []; let n = hit
  for (let i=0;i<8 && n;i++){ chain.push(pick(n)); n = n.parentElement }
  return { chain }
})
console.log(JSON.stringify(out, null, 1))
await b.close()
