/**
 * Pull the Vehicle Register branded .xlsx from LIVE prod by clicking the real
 * "Export to Excel" button as the CFO, so the logo can be opened in Excel.
 * Read-only: the export endpoint is a GET, nothing is written to prod.
 *
 *   node fetch-vehicle-export.mjs <out.xlsx>
 */
import { BASE, openBrowser, newRolePage, gotoPath, settle, clickByText } from './lib.mjs';

const out = process.argv[2] || 'vehicle-export-prod.xlsx';

const browser = await openBrowser();
const { page } = await newRolePage(browser, { role: 'admin', width: 1280 });
await gotoPath(page, '/vehicle-register');
await settle(page);

// omni stacks global modals ("N tasks need your action", new-task toasts) over
// every page and they swallow clicks. They are unrelated to this feature, so
// strip the overlays in THIS browser tab only — nothing is sent to the server.
const removed = await page.evaluate(() => {
  const kill = [...document.querySelectorAll('div.fixed.inset-0')];
  kill.forEach(n => n.remove());
  return kill.length;
});
console.log(`dismissed ${removed} blocking overlay(s)`);
await settle(page);

await clickByText(page, 'Reports');
await settle(page);

const [download] = await Promise.all([
  page.waitForEvent('download', { timeout: 60000 }),
  clickByText(page, 'Export to Excel'),
]);
await download.saveAs(out);
await browser.close();

console.log(`OK  saved ${out}`);
console.log(`suggested filename from server: ${download.suggestedFilename()}`);
console.log(`clicked the real button on ${BASE}/vehicle-register (Reports tab)`);
