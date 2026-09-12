import { openBrowser, newRolePage, gotoPath, settle, shoot } from './lib.mjs';
const browser = await openBrowser();
const { page } = await newRolePage(browser, { role: 'admin', width: 1280 });
await gotoPath(page, '/hris/disciplinary');
await settle(page);
await page.waitForTimeout(9000);
// what the page's own JS sees from the API
const data = await page.evaluate(async () => {
  try {
    const r = await fetch('/hris/api/disciplinary/', { headers: { Accept: 'application/json' } });
    const j = await r.json();
    return { status: r.status, me: j.me,
      cases: (j.cases||[]).map(c => ({ s: c.subject, cat: c.category_label, st: c.status_label,
        d: c.incident_date, by: c.raised_by })) };
  } catch (e) { return { err: String(e) }; }
});
console.log(JSON.stringify(data, null, 1));
// and what the user actually sees on screen
const txt = await page.evaluate(() => document.body.innerText.replace(/\n{2,}/g,'\n').slice(0, 1800));
console.log('---- VISIBLE TEXT ----');
console.log(txt);
await shoot(page, 'out-disc/disciplinary-loaded.png');
await browser.close();
