// Walk a whole feature step by step and stitch every step into ONE picture.
//
//   node omni-journey.mjs journey.json
//
// journey.json looks like this:
// {
//   "name": "Raise an internal audit finding",
//   "as": "staff",
//   "width": 1120,
//   "steps": [
//     { "go": "/internal-audit/findings", "caption": "Findings list" },
//     { "click": "New finding",           "caption": "The pop-up" },
//     { "type": { "label": "Title", "text": "Test finding" }, "caption": "Filled in" }
//   ]
// }

import fs from 'node:fs';
import path from 'node:path';
import { openPage, gotoPath, shoot, clickByText, settle, verdict, contactSheet, SHOT_DIR, slug, stamp } from './lib.mjs';

const specFile = process.argv[2];
if (!specFile) {
  console.error('Usage: node omni-journey.mjs <journey.json>');
  process.exit(1);
}
const spec = JSON.parse(fs.readFileSync(specFile, 'utf8'));
const role = (spec.as || 'staff').toLowerCase();
const width = Number(spec.width || 1120);
const name = spec.name || path.basename(specFile, '.json');
const workDir = path.join(SHOT_DIR, `journey-${slug(name)}-${stamp()}`);

const { browser, page, consoleErrors } = await openPage({ role, width, anonymous: role === 'anon' });
const frames = [];
let lastStatus = null;

try {
  for (const [i, step] of (spec.steps || []).entries()) {
    if (step.go) ({ status: lastStatus } = await gotoPath(page, step.go));
    if (step.click) await clickByText(page, step.click);
    if (step.type) {
      const box = step.type.label
        ? page.getByLabel(step.type.label, { exact: false }).first()
        : page.locator(step.type.selector).first();
      await box.fill(String(step.type.text ?? ''));
      await settle(page);
    }
    if (step.wait) await page.waitForTimeout(Number(step.wait));

    const file = path.join(workDir, `${String(i + 1).padStart(2, '0')}-${slug(step.caption || step.go || step.click || 'step')}.png`);
    await shoot(page, file);
    const v = await verdict(page, lastStatus, consoleErrors);
    frames.push({ file, caption: `${i + 1}. ${step.caption || step.go || step.click || 'step'}`, state: v.state, note: v.why });
    console.log(`  ${String(i + 1).padStart(2)}. ${v.state.padEnd(8)} ${step.caption || step.go || step.click}`);
  }
} finally {
  await browser.close();
}

const sheet = path.join(SHOT_DIR, `journey-${slug(name)}-${stamp()}.png`);
await contactSheet(frames, sheet, { title: `${name}  -  as ${role}, ${width}px`, columns: 2 });
console.log(`\n  One picture of the whole journey: ${sheet}`);
console.log(`  Individual steps: ${workDir}`);
process.exitCode = frames.some((f) => ['BROKEN', 'BLANK'].includes(f.state)) ? 1 : 0;
