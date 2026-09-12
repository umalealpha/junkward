import { chromium } from 'playwright';
const URL = 'https://omni.alphadirect.co.bw/login?preview=1';
const sizes = [
  ['desktop-1280x800', 1280, 800],
  ['laptop-1280x700', 1280, 700],
  ['laptop-1366x768', 1366, 768],
  ['mobile-375x812', 375, 812],
];
let browser;
try { browser = await chromium.launch(); }
catch (e) { browser = await chromium.launch({ channel: 'chrome' }); }
for (const [name, w, h] of sizes) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h } });
  const page = await ctx.newPage();
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 45000 }).catch(()=>{});
  await page.waitForTimeout(3500); // let map + rise animations settle
  // measure overlap live on prod
  const m = await page.evaluate(() => {
    const r = el => { if(!el) return null; const b=el.getBoundingClientRect(); return {t:Math.round(b.top),b:Math.round(b.bottom),l:Math.round(b.left),ri:Math.round(b.right)}; };
    const sub = r(document.querySelector('.subtitle'));
    const cta = r(document.querySelector('.cta'));
    return { sub, cta, gap: (sub&&cta)?cta.t-sub.b:null, vp:[innerWidth,innerHeight] };
  });
  await page.screenshot({ path: `qc-out/login-${name}.png` });
  console.log(name, JSON.stringify(m));
  await ctx.close();
}
await browser.close();
