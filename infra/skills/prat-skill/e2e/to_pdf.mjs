import { chromium } from 'playwright';
const url = process.argv[2];
const out = process.argv[3];
const b = await chromium.launch();
const p = await b.newPage();
await p.goto(url, { waitUntil: 'networkidle' });
await p.pdf({ path: out, format: 'A4', printBackground: true,
             margin: { top: '10mm', bottom: '10mm', left: '8mm', right: '8mm' } });
await b.close();
console.log('pdf ->', out);
