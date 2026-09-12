import { chromium } from 'playwright'
import { readFileSync } from 'fs'; import { homedir } from 'os'; import { join } from 'path'
const tok = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim()
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } })
await ctx.addInitScript(t => localStorage.setItem('alpha_token', t), tok)
const p = await ctx.newPage()
await p.goto('https://omni.alphadirect.co.bw/purchase-orders'); await p.waitForTimeout(6000)
const out = await p.evaluate(() => {
  const tr = document.querySelector('table tbody tr'); if (!tr) return 'no tr'
  const hits = []
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules } catch { continue }
    const walk = rs => { for (const r of rs) {
      if (r.cssRules) { walk(r.cssRules); continue }
      if (!r.selectorText || !r.style) continue
      if (!/background/.test(r.style.cssText)) continue
      for (const sel of r.selectorText.split(',')) {
        const s = sel.trim()
        try { if (tr.matches(s)) hits.push({ sel: s, css: r.style.cssText.slice(0,160), href: (sheet.href||'inline').split('/').pop() }) } catch {}
      } } }
    walk(rules)
  }
  return hits
})
console.log(JSON.stringify(out, null, 1))
await b.close()
