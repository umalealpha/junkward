import { chromium } from 'playwright'
import { readFileSync } from 'fs'; import { homedir } from 'os'; import { join } from 'path'
const tok = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim()
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } })
await ctx.addInitScript(t => localStorage.setItem('alpha_token', t), tok)
const p = await ctx.newPage()
await p.goto('https://omni.alphadirect.co.bw/purchase-orders')
await p.waitForTimeout(9000)
console.log('URL', p.url())
console.log('TABLES', await p.evaluate(()=>document.querySelectorAll('table').length))
console.log('TEXT', (await p.evaluate(()=>document.body.innerText)).slice(0,600).replace(/\n+/g,' | '))
await b.close()
