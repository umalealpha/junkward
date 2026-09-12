// One-off: full-page screenshot of /company-cards through the read-only QC token
// (same token source as qc.mjs — read from ~/.omni-qa-token, never printed).
import { chromium } from 'playwright'
import { readFileSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'

const BASE = process.env.OMNI_BASE || 'https://omni.alphadirect.co.bw'
let token = process.env.OMNI_TOKEN
if (!token) { try { token = readFileSync(join(homedir(), '.omni-qa-token'), 'utf8').trim() } catch {} }
if (!token) { console.error('NO_TOKEN: run qc.sh first'); process.exit(2) }

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 2 })
await ctx.addInitScript(t => {
  localStorage.setItem('alpha_token', t)
  localStorage.setItem('alpha_qa_readonly', '1')
  localStorage.setItem('alpha_theme', 'professional')
}, token)
const page = await ctx.newPage()
await page.goto(BASE + '/company-cards', { waitUntil: 'networkidle', timeout: 45000 })
await page.waitForTimeout(2500)
try { await page.getByText('Card spends').first().scrollIntoViewIfNeeded({ timeout: 8000 }) } catch {}
await page.waitForTimeout(1000)
// prove the row is present in the DOM before shooting
const hasRow = await page.getByText('Sefalana Shopper Setlhoa').first().isVisible().catch(() => false)
await page.screenshot({ path: 'bica_company_cards_full.png', fullPage: true })
console.log('shot: bica_company_cards_full.png  | BICA row visible in DOM:', hasRow)
await b.close()
