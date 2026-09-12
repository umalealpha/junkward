import { chromium } from 'playwright'
import { readFileSync } from 'fs'
import { homedir } from 'os'
import { join } from 'path'

const token = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim()
const BASE = 'https://omni.alphadirect.co.bw'
const url = `${BASE}/compliance/dpo/f693fc7a-4756-473e-9658-9e206f8d645b`

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 1 })
await ctx.addInitScript((t) => {
  localStorage.setItem('alpha_token', t)
  localStorage.setItem('alpha_qa_readonly', '1')
  localStorage.setItem('alpha_theme', 'professional')
}, token)
const page = await ctx.newPage()
await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)
// scroll to the full-form heading if present
try { await page.getByText('Full DPIA form', { exact: false }).scrollIntoViewIfNeeded({ timeout: 4000 }) } catch {}
await page.waitForTimeout(500)
await page.screenshot({ path: 'dpo_fullform_ok.png', fullPage: true })
console.log('done url=', page.url())
await b.close()
