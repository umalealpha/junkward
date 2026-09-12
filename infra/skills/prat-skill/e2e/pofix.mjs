import { chromium } from 'playwright'
import { readFileSync } from 'fs'; import { homedir } from 'os'; import { join } from 'path'
const tok = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim()
// the exact rules from the patched globals.css, replacing the broken ones
const PATCH = `
html.theme-professional [class*="bg-[#F07F00"]:not([class*=":bg-[#"]),
html.theme-professional [class*="bg-[#F4A623"]:not([class*=":bg-[#"]),
html.theme-professional [class*="bg-[#FF9F2E"]:not([class*=":bg-[#"]),
html.theme-professional [class*="bg-[#0B0B3B"]:not([class*=":bg-[#"]),
html.theme-professional [class*="bg-[#0D1B2A"]:not([class*=":bg-[#"]),
html.theme-professional [class*="bg-[#07074E"]:not([class*=":bg-[#"]),
html.theme-professional [class*="bg-[#1A1A5E"]:not([class*=":bg-[#"]) { background-color:#4F6BED !important; }
html.theme-professional [class*="hover:bg-[#F4A623]/"]:hover { background-color:#F7F8FA !important; }
`
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 })
await ctx.addInitScript(t => localStorage.setItem('alpha_token', t), tok)
const p = await ctx.newPage()
await p.goto('https://omni.alphadirect.co.bw/purchase-orders'); await p.waitForTimeout(6000)
const before = await p.evaluate(()=>getComputedStyle(document.querySelector('table tbody tr')).backgroundColor)
// remove the two broken rules, add the fixed ones
await p.evaluate(patch => {
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules } catch { continue }
    for (let i = rules.length - 1; i >= 0; i--) {
      const r = rules[i]
      if (r.selectorText && /theme-professional \[class\*="bg-\[#/.test(r.selectorText) && !/:not\(/.test(r.selectorText)) sheet.deleteRule(i)
    }
  }
  const s = document.createElement('style'); s.textContent = patch; document.head.appendChild(s)
}, PATCH)
await p.waitForTimeout(800)
const after = await p.evaluate(()=>{
  const tr = document.querySelector('table tbody tr')
  const th = document.querySelector('table thead tr')
  return { row: getComputedStyle(tr).backgroundColor, head: getComputedStyle(th).backgroundColor }
})
console.log('row background BEFORE fix:', before)
console.log('row background AFTER  fix:', after.row, '| header stays:', after.head)
await p.screenshot({ path: 'po_after_fix.png', fullPage: false })
await b.close()
