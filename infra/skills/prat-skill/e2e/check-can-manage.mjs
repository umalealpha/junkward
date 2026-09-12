/**
 * Read-only: confirm the LIVE board endpoint returns the new `can_manage` flag
 * and report what the signed-in role sees. Proves the deployed image has the
 * fleet-admin gate, not just my local build.
 *
 *   node check-can-manage.mjs [admin|staff]
 */
import { BASE, openBrowser, newRolePage, gotoPath, settle } from './lib.mjs';

const role = process.argv[2] || 'admin';
const browser = await openBrowser();
const { page } = await newRolePage(browser, { role, width: 1280 });

// Observe the board response the APP itself makes (it carries the real auth
// header); don't try to re-issue the request by hand.
let captured = null;
page.on('response', async (res) => {
  if (!res.url().includes('/vehicle-register/board/')) return;
  try {
    const body = await res.json();
    captured = {
      status: res.status(),
      hasField: Object.prototype.hasOwnProperty.call(body, 'can_manage'),
      canManage: body.can_manage,
      vehicles: Array.isArray(body.vehicles) ? body.vehicles.length : null,
    };
  } catch { captured = { status: res.status(), parseError: true }; }
});

await gotoPath(page, '/vehicle-register');
await settle(page);

const out = {
  ...(captured || { note: 'board response never seen' }),
  addButtonVisible: await page.evaluate(
    () => document.body.innerText.includes('+ Add vehicle')),
};

await browser.close();
console.log(`role=${role}  ${BASE}/api/v1/nexus/vehicle-register/board/`);
console.log(JSON.stringify(out, null, 2));
