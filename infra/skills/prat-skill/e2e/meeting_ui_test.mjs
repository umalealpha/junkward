// Meeting Mode UI test — drives the REAL Record button in ARIA's HUD with a fake
// camera + a recorded speech clip as the fake microphone, against the isolated
// dry-run backend on :8099. Proves: button renders, recording starts, upload
// happens, and the pipeline reaches "done" — with no console errors from our code.
import { chromium } from 'playwright';

const SP = 'C:\\Users\\PRATHA~1\\AppData\\Local\\Temp\\claude\\C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye\\e75eb58d-eaf2-4678-b08d-32d3dc5c6b84\\scratchpad';
const WAV = SP + '\\speech.wav';
const SHOT = SP + '\\meeting_test.png';
const HUD = 'http://127.0.0.1:8099/hud/hud.html';

const browser = await chromium.launch({
  headless: true,
  args: [
    '--use-fake-device-for-media-stream',
    '--use-fake-ui-for-media-stream',
    '--use-file-for-fake-audio-capture=' + WAV,
    '--autoplay-policy=no-user-gesture-required',
  ],
});
const ctx = await browser.newContext({ permissions: ['microphone', 'camera'], viewport: { width: 1280, height: 800 } });
const page = await ctx.newPage();
await page.route(/127\.0\.0\.1:8080/, r => r.abort());   // isolate from the live app
const cerr = [];
page.on('console', m => { if (m.type() === 'error') cerr.push(m.text()); });
page.on('pageerror', e => cerr.push('PAGEERROR: ' + e.message));

await page.goto(HUD, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(3500);

const btn = await page.$('#meetbtn');
console.log('RECORD BUTTON:', btn ? JSON.stringify((await btn.textContent()).trim()) : 'MISSING');

await page.click('#meetingcard');
await page.waitForTimeout(1500);
console.log('AFTER START  :', JSON.stringify((await page.$eval('#meetbtn', e => e.textContent)).trim()),
            '| status:', JSON.stringify((await page.$eval('#meetstatus', e => e.textContent)).trim()));

await page.waitForTimeout(2500);
await page.locator('#meetingcard').screenshot({ path: SP + '\\meeting_rec.png' });  // the card while recording
await page.waitForTimeout(6500);     // record ~9s total of the fake-mic speech
await page.click('#meetingcard');    // stop
console.log('STOPPED — processing...');

let st = {};
for (let i = 0; i < 45; i++) {
  await page.waitForTimeout(2000);
  try { st = await page.evaluate(async () => await (await fetch('/assistant/meeting/status')).json()); } catch (e) {}
  process.stdout.write(' ' + (st.phase || '?'));
  if (st.phase === 'done' || st.phase === 'error') break;
}
console.log('\nFINAL STATUS :', JSON.stringify(st));
console.log('UI LINE      :', JSON.stringify((await page.$eval('#meetstatus', e => e.textContent).catch(() => '?'))));
await page.screenshot({ path: SHOT });
const mErr = cerr.filter(e => /meeting|record|MediaRecorder|getUserMedia/i.test(e));
console.log('MEETING JS ERRORS:', mErr.length ? mErr.slice(0, 5) : 'none');
await browser.close();
