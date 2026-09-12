import { openBrowser, newRolePage, gotoPath, settle } from '../lib.mjs'
const MARK = 'CFO Command Centre', MARK2 = 'Awaiting your approval'
const browser = await openBrowser()
const out = {}
const { page: admin } = await newRolePage(browser, { role: 'admin', width: 1320 })
await gotoPath(admin, '/dashboard'); await settle(admin); await admin.waitForTimeout(6000)
let t = await admin.evaluate(() => document.body.innerText)
out.admin_has_band = t.includes(MARK); out.admin_has_approvals = t.includes(MARK2)
await gotoPath(admin, '/cfo'); await admin.waitForTimeout(3500)
out.cfo_url = admin.url(); out.cfo_redirected = admin.url().replace(/[#?].*$/,'').endsWith('/dashboard')
const { page: staff } = await newRolePage(browser, { role: 'staff', width: 1320 })
await gotoPath(staff, '/dashboard'); await settle(staff); await staff.waitForTimeout(6000)
let ts = await staff.evaluate(() => document.body.innerText)
out.staff_has_band = ts.includes(MARK); out.staff_url = staff.url()
console.log(JSON.stringify(out, null, 2))
await browser.close()
