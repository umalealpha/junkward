// Diagnostic: open the create modal, dump its fields, screenshot. Read-only.
import { openBrowser, newRolePage, gotoPath, settle, clickByText, shoot, stamp } from './lib.mjs'

const OUT = `shots/repro-newpayee-${stamp()}.png`
const browser = await openBrowser()
const { page } = await newRolePage(browser, { role: 'admin', width: 1280, height: 1600 })
try {
  await gotoPath(page, '/payment-requests')
  await settle(page)
  await clickByText(page, 'New payment request')
  await page.waitForTimeout(1000)
  await clickByText(page, 'Operations payment').catch(e => console.log('no Operations btn:', e.message))
  await page.waitForTimeout(400)
  await clickByText(page, 'Supplier payments').catch(e => console.log('no Supplier btn:', e.message))
  await page.waitForTimeout(600)
  const fields = await page.evaluate(() => {
    const modal = document.querySelector('[class*="max-w-2xl"]') || document.body
    const inputs = [...modal.querySelectorAll('input,textarea,select')].map(el => ({
      tag: el.tagName.toLowerCase(), type: el.type || '', placeholder: el.placeholder || '',
      name: el.name || '', value: (el.value || '').slice(0, 30),
    }))
    const labels = [...modal.querySelectorAll('label')].map(l => l.innerText.trim().replace(/\s+/g, ' ').slice(0, 40)).filter(Boolean)
    return { inputs, labels }
  })
  console.log('LABELS:', JSON.stringify(fields.labels, null, 0))
  console.log('INPUTS:', JSON.stringify(fields.inputs, null, 0))
  await shoot(page, OUT)
  console.log('shot:', OUT)
} catch (e) {
  console.log('ERR:', e.message)
  await shoot(page, OUT).catch(() => {})
} finally {
  await browser.close()
}
