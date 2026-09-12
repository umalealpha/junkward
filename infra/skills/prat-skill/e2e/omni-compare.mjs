// Old version vs new version, side by side in one picture.
//
//   node omni-compare.mjs "/dashboard" --a https://omni.alphadirect.co.bw --b http://localhost:3000
//   node omni-compare.mjs "/dashboard" --a PROD --b NEW --as admin --width 1280

import path from 'node:path';
import { openPage, gotoPath, shoot, verdict, contactSheet, parseArgs, unmangle, BASE, SHOT_DIR, slug, stamp } from './lib.mjs';

const { positional, flags } = parseArgs(process.argv.slice(2));
const flag = (n, d) => flags[n] ?? d;

const target = unmangle(positional[0] || '');
if (!target) {
  console.error('Usage: node omni-compare.mjs "<path>" --a <old base url> --b <new base url> [--as staff] [--width 1120]');
  process.exit(1);
}

const a = flag('a', BASE);
const b = flag('b', 'http://localhost:3000');
const role = (flag('as', 'staff') || 'staff').toLowerCase();
const width = Number(flag('width', 1120));
const dir = path.join(SHOT_DIR, `compare-${slug(target)}-${stamp()}`);

const frames = [];
for (const [label, base] of [['BEFORE  ' + a, a], ['AFTER  ' + b, b]]) {
  const { browser, page, consoleErrors } = await openPage({ role, width, anonymous: role === 'anon' });
  try {
    const url = base.replace(/\/$/, '') + (target.startsWith('/') ? target : '/' + target);
    const { status } = await gotoPath(page, url);
    const file = path.join(dir, `${slug(label)}.png`);
    await shoot(page, file);
    const v = await verdict(page, status, consoleErrors);
    frames.push({ file, caption: label, state: v.state, note: v.why });
    console.log(`  ${v.state.padEnd(8)} ${url}`);
  } finally {
    await browser.close();
  }
}

const sheet = path.join(SHOT_DIR, `compare-${slug(target)}-${stamp()}.png`);
await contactSheet(frames, sheet, { title: `${target}  -  before vs after (as ${role}, ${width}px)`, columns: 2, width: 2100 });
console.log(`\n  Side by side: ${sheet}`);
