import { chromium } from 'playwright';
const url = 'file:///C:/Users/PRATHA~1/AppData/Local/Temp/claude/C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye/e8239cc9-10b0-4741-938a-19aa627e1b6a/scratchpad/ropa_mock.html';
let b;
try { b = await chromium.launch(); }
catch(e){ b = await chromium.launch({ channel:'chrome' }); }
const p = await b.newPage({ viewport:{ width:780, height:960 } });
await p.goto(url, { waitUntil:'load' });
await p.screenshot({ path:'dpo-out/ropa_mock_780.png', fullPage:true });
await b.close();
console.log('shot saved');
