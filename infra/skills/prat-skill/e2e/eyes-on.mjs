// The one command. Shoots a screen as BOTH the admin and the non-admin staff
// account, at 1120 and 1280 pixels, and glues all four into one picture.
//
//   node eyes-on.mjs "/internal-audit/findings"
//   node eyes-on.mjs "/internal-audit/findings" --click "New finding"
//
// This is the ship gate: no screen goes live until this picture has been looked at.

import path from 'node:path';
import fs from 'node:fs';
import {
  openBrowser, newRolePage, gotoPath, shoot, clickByText, verdict, contactSheet,
  parseArgs, unmangle, sessionPath, WIDTHS, ROLES, SHOT_DIR, slug, stamp,
} from './lib.mjs';

const { positional, flags } = parseArgs(process.argv.slice(2));
const target = unmangle(positional[0] || '');
if (!target) {
  console.error('Usage: node eyes-on.mjs "<path>" [--click "Button text"] [--widths 1120,1280]');
  process.exit(1);
}
const click = flags.click || null;
const widths = (flags.widths ? String(flags.widths).split(',') : WIDTHS).map(Number);

const roles = Object.keys(ROLES).filter((r) => {
  if (fs.existsSync(sessionPath(r))) return true;
  console.log(`  skipping ${r}: no saved login yet (run: node omni-login.mjs ${r})`);
  return false;
});
if (!roles.length) {
  console.error('\n  No saved logins at all. Run "node omni-login.mjs staff" first.\n');
  process.exit(1);
}

const runStamp = stamp();
const dir = path.join(SHOT_DIR, `eyes-on-${slug(target)}-${runStamp}`);
const browser = await openBrowser();
const frames = [];

console.log(`\n  ${target}${click ? `  ->  click "${click}"` : ''}\n`);

for (const role of roles) {
  for (const width of widths) {
    const { context, page, consoleErrors } = await newRolePage(browser, { role, width });
    try {
      const { status } = await gotoPath(page, target);
      if (click) {
        try { await clickByText(page, click); }
        catch { consoleErrors.push(`could not find "${click}" on this screen`); }
      }
      const file = path.join(dir, `${role}-${width}.png`);
      await shoot(page, file);
      const v = await verdict(page, status, consoleErrors);
      frames.push({ file, caption: `${ROLES[role].label} @ ${width}px`, state: v.state, note: v.why });
      console.log(`  ${v.state.padEnd(9)} ${ROLES[role].label} @ ${width}px${v.why ? '   (' + v.why + ')' : ''}`);
    } finally {
      await context.close();
    }
  }
}

await browser.close();

const sheet = path.join(SHOT_DIR, `eyes-on-${slug(target)}-${runStamp}.png`);
await contactSheet(frames, sheet, {
  title: `${target}${click ? `  ->  "${click}"` : ''}`,
  columns: 2,
  width: 1900,
});

console.log(`\n  Look at this one picture: ${sheet}\n`);
process.exitCode = frames.some((f) => ['BROKEN', 'BLANK', 'BLOCKED'].includes(f.state)) ? 1 : 0;
