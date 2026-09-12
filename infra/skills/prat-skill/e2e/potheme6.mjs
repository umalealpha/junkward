import { chromium } from 'playwright'
import { readFileSync } from 'fs'; import { homedir } from 'os'; import { join } from 'path'
const tok = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim()
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } })
await ctx.addInitScript(t => localStorage.setItem('alpha_token', t), tok)
const p = await ctx.newPage()
await p.goto('https://omni.alphadirect.co.bw/purchase-orders'); await p.waitForTimeout(6000)
console.log(JSON.stringify(await p.evaluate(() => {
  const out = []
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules } catch { out.push({cors: sheet.href}); continue }
    const walk = rs => { for (const r of rs) {
      if (r.cssRules) { walk(r.cssRules); continue }
      if (r.selectorText && /theme-professional/.test(r.selectorText) && /background/.test(r.style?.cssText||''))
        out.push({ sel: r.selectorText.slice(0,200), css: r.style.cssText.slice(0,180), href: (sheet.href||'inline').split('/').pop() })
    } }
    walk(rules)
  }
  return out.slice(0, 40)
}), null, 1))
await b.close()
