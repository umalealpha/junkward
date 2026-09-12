import { chromium } from 'playwright'
import { readFileSync } from 'fs'; import { homedir } from 'os'; import { join } from 'path'
const tok = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim()
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } })
await ctx.addInitScript(t => localStorage.setItem('alpha_token', t), tok)
const p = await ctx.newPage()
await p.goto('https://omni.alphadirect.co.bw/purchase-orders'); await p.waitForTimeout(6000)
console.log(JSON.stringify(await p.evaluate(() => {
  const tr = document.querySelector('table tbody tr')
  const thead = document.querySelector('table thead tr')
  const g = e => e ? { inline: e.getAttribute('style'), attrs: [...e.attributes].map(a=>a.name+'='+a.value).join(' ').slice(0,300), bg: getComputedStyle(e).backgroundColor } : null
  return { tr: g(tr), thead: g(thead), htmlClass: document.documentElement.className, bodyClass: document.body.className.slice(0,200) }
}), null, 1))
await b.close()
