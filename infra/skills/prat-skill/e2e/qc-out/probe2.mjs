import { openBrowser, newRolePage, gotoPath, settle } from '../lib.mjs'
const browser = await openBrowser()
const { page: admin } = await newRolePage(browser, { role: 'admin', width: 1320 })
const hits = []
admin.on('response', r => { const u=r.url(); if (u.includes('/dashboard/cfo')) hits.push({url:u, status:r.status()}) })
await gotoPath(admin, '/dashboard'); await settle(admin); await admin.waitForTimeout(7000)
const bodyHasBand = (await admin.evaluate(()=>document.body.innerText)).includes('CFO Command Centre')
// also check a general authed call to see if the whole session is stale
const meStatus = await admin.evaluate(async () => {
  try { const r = await fetch('/api/v1/dashboard/cfo/', {headers:{Authorization:'Bearer '+(localStorage.getItem('alpha_token')||'')}}); return r.status } catch(e){ return 'ERR:'+e.message }
})
console.log(JSON.stringify({ cfo_endpoint_hits: hits, band_visible: bodyHasBand, direct_fetch_status: meStatus }, null, 2))
await browser.close()
