import { chromium } from 'playwright'
import { readFileSync } from 'fs'; import { homedir } from 'os'; import { join } from 'path'
const tok = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim()
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } })
await ctx.addInitScript(t => localStorage.setItem('alpha_token', t), tok)
const p = await ctx.newPage()
await p.goto('https://omni.alphadirect.co.bw/purchase-orders'); await p.waitForTimeout(6000)
const cdp = await ctx.newCDPSession(p)
await cdp.send('DOM.enable'); await cdp.send('CSS.enable')
const { root } = await cdp.send('DOM.getDocument', { depth: -1, pierce: true })
const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: 'table tbody tr' })
const m = await cdp.send('CSS.getMatchedStylesForNode', { nodeId })
const hits = []
for (const e of (m.matchedCSSRules||[])) {
  const css = (e.rule.style?.cssText)||''
  if (/background/.test(css)) hits.push({ sel: e.rule.selectorList.text.slice(0,160), css: css.slice(0,200), origin: e.rule.origin, src: e.rule.styleSheetId })
}
console.log('MATCHED-BG', JSON.stringify(hits, null, 1))
console.log('INHERITED', JSON.stringify((m.inherited||[]).flatMap(i=>(i.matchedCSSRules||[]).filter(e=>/background/.test(e.rule.style?.cssText||'')).map(e=>({sel:e.rule.selectorList.text.slice(0,120), css:e.rule.style.cssText.slice(0,120)}))).slice(0,10), null, 1))
await b.close()
