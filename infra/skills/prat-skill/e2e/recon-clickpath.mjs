// READ-ONLY proof that the Supplier Recon click-path works on the live site.
//
//   node recon-clickpath.mjs
//
// Expands a supplier row, then reports whether the reason dropdown is populated
// and the Record / Escalate buttons are present and correctly disabled. It
// NEVER submits — nothing is written to prod (f-never-write).

import path from 'node:path';
import { openPage, gotoPath, shoot, settle, SHOT_DIR, stamp } from './lib.mjs';

const { browser, page, consoleErrors } = await openPage({ role: 'admin', width: 1400 });
const out = path.join(SHOT_DIR, `recon-clickpath-${stamp()}.png`);

try {
  await gotoPath(page, '/payables/recon');
  await settle(page);
  await page.waitForTimeout(3500);

  // The taskboard reminder ("N tasks need your action") renders a full-screen
  // overlay that intercepts every click on this page until it is dismissed.
  // Removing it in THIS browser only — no prod data is touched.
  const overlaysRemoved = await page.evaluate(() => {
    let n = 0;
    document.querySelectorAll('div.fixed.inset-0').forEach((el) => {
      const cs = getComputedStyle(el);
      if (cs.position === 'fixed' && el.getBoundingClientRect().width > 300) {
        el.remove();
        n += 1;
      }
    });
    return n;
  });
  await settle(page);

  const rows = page.locator('table tbody tr');
  const before = await rows.count();

  // Click the first supplier row to expand its bills.
  await rows.first().click({ timeout: 8000 });
  await settle(page);
  await page.waitForTimeout(2500);

  const after = await rows.count();

  const probe = await page.evaluate(() => {
    const selects = [...document.querySelectorAll('select')];
    const reason = selects.find((s) =>
      [...s.options].some((o) => /not paid|reason/i.test(o.textContent || '')));
    const buttons = [...document.querySelectorAll('button')].map((b) => ({
      text: (b.textContent || '').trim().slice(0, 30),
      disabled: b.disabled,
    })).filter((b) => b.text);
    const textareas = [...document.querySelectorAll('textarea')];
    return {
      reasonDropdownFound: !!reason,
      reasonOptionCount: reason ? reason.options.length : 0,
      firstReasons: reason
        ? [...reason.options].slice(1, 6).map((o) => (o.textContent || '').trim())
        : [],
      justificationBoxes: textareas.length,
      justificationPlaceholder: textareas[0]
        ? (textareas[0].placeholder || '').slice(0, 60) : null,
      recordButton: buttons.find((b) => /^Record$/i.test(b.text)) || null,
      escalateButton: buttons.find((b) => /^Escalate$/i.test(b.text)) || null,
      signOffButton: buttons.find((b) => /Sign off/i.test(b.text)) || null,
      excelButton: buttons.find((b) => /Excel/i.test(b.text)) || null,
      ownerLine: (document.body.innerText.match(/Owner:\s*([^\n·]+)/) || [])[1] || null,
      notInLedgerPills: (document.body.innerText.match(/Not in ledger/g) || []).length,
      billRefs: (document.body.innerText.match(/BILL-\d{4}-\d+/g) || []).slice(0, 3),
    };
  });

  await shoot(page, out);

  console.log('\n  LIVE CLICK-PATH — Supplier Recon (nothing was submitted)\n');
  console.log('  blocking overlays removed :', overlaysRemoved,
              '(taskboard reminder covers the page until dismissed)');
  console.log('  rows before click :', before);
  console.log('  rows after click  :', after, after > before ? '(row expanded)' : '(NOT expanded)');
  console.log('  owner on board    :', probe.ownerLine);
  console.log('  bills shown       :', probe.billRefs.join(', ') || '(none)');
  console.log('  "Not in ledger"   :', probe.notInLedgerPills);
  console.log('  reason dropdown   :', probe.reasonDropdownFound,
              `(${probe.reasonOptionCount} options)`);
  console.log('  sample reasons    :', probe.firstReasons.join(' / '));
  console.log('  justification box :', probe.justificationBoxes,
              probe.justificationPlaceholder ? `"${probe.justificationPlaceholder}…"` : '');
  console.log('  Record button     :', JSON.stringify(probe.recordButton));
  console.log('  Escalate button   :', JSON.stringify(probe.escalateButton));
  console.log('  Sign off button   :', JSON.stringify(probe.signOffButton));
  console.log('  Excel button      :', JSON.stringify(probe.excelButton));
  if (consoleErrors.length) {
    console.log('\n  console errors    :', consoleErrors.length);
    consoleErrors.slice(0, 4).forEach((e) => console.log('    -', String(e).slice(0, 140)));
  }
  console.log('\n  picture:', out, '\n');
} finally {
  await browser.close();
}
