// One-off: screenshot a local HTML file to PNG. Args: <htmlPath> <outPng> [width]
import { chromium } from 'playwright';
import { pathToFileURL } from 'url';

const [htmlPath, outPng, widthArg] = process.argv.slice(2);
const width = parseInt(widthArg || '700', 10);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height: 1000 }, deviceScaleFactor: 2 });
await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'networkidle' });
await page.screenshot({ path: outPng, fullPage: true });
await browser.close();
console.log('wrote', outPng);
