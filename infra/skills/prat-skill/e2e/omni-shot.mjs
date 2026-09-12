// One screenshot of one omni screen.
//
//   node omni-shot.mjs "/commissions" out.png --width 1120 --as staff
//   node omni-shot.mjs "/internal-audit/findings" out.png --click "New finding"
//
// --as      admin | staff | anon   (default staff - the non-admin test account)
// --width   viewport width in pixels (default 1120)
// --click   text of a button/link to press before shooting (opens the pop-up)

import path from 'node:path';
import { openPage, gotoPath, shoot, clickByText, verdict, parseArgs, unmangle, SHOT_DIR, slug, stamp } from './lib.mjs';

const { positional, flags } = parseArgs(process.argv.slice(2));
const flag = (name, fallback) => flags[name] ?? fallback;

const target = unmangle(positional[0] || '');
if (!target) {
  console.error('Usage: node omni-shot.mjs "<path>" [out.png] [--as admin|staff|anon] [--width 1120] [--click "Button text"]');
  process.exit(1);
}

const role = (flag('as', 'staff') || 'staff').toLowerCase();
const width = Number(flag('width', 1120));
const click = flag('click', null);
const out = positional[1] || path.join(SHOT_DIR, `${slug(target)}-${role}-${width}-${stamp()}.png`);

const { browser, page, consoleErrors, sessionAgeDays } = await openPage({
  role, width, anonymous: role === 'anon',
});

try {
  const { url, status } = await gotoPath(page, target);
  if (click) await clickByText(page, click);
  await shoot(page, out);
  const v = await verdict(page, status, consoleErrors);

  console.log(`  ${v.state}${v.why ? ` - ${v.why}` : ''}`);
  console.log(`  ${url}  (as ${role}, ${width}px, http ${status})`);
  if (sessionAgeDays > 14) console.log(`  note: saved login is ${Math.round(sessionAgeDays)} days old - re-run omni-login.mjs if pages look signed out.`);
  console.log(`  saved: ${out}`);
  if (consoleErrors.length) console.log(`  console: ${consoleErrors.slice(0, 3).join(' | ')}`);

  process.exitCode = ['BROKEN', 'BLANK'].includes(v.state) ? 1 : 0;
} finally {
  await browser.close();
}
