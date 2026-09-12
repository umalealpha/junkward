import { chromium } from 'playwright';
const url='file:///C:/Users/PRATHA~1/AppData/Local/Temp/claude/C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye/e8239cc9-10b0-4741-938a-19aa627e1b6a/scratchpad/quote_big.html';
const pdf='C:/Users/PRATHA~1/AppData/Local/Temp/claude/C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye/e8239cc9-10b0-4741-938a-19aa627e1b6a/scratchpad/Alpha_Direct_Quotation_Prathap_Cigarettes.pdf';
let b; try{b=await chromium.launch();}catch(e){b=await chromium.launch({channel:'chrome'});}
const p=await b.newPage({viewport:{width:794,height:1123},deviceScaleFactor:1.4});
await p.goto(url,{waitUntil:'load'});
await p.screenshot({path:'dpo-out/quote_big.png',fullPage:true});
await p.pdf({path:pdf, format:'A4', printBackground:true, margin:{top:'0',bottom:'14mm',left:'0',right:'0'},
  displayHeaderFooter:true, headerTemplate:'<div></div>',
  footerTemplate:'<div style="width:100%;font-family:Arial;font-size:8px;color:#6B7280;padding:0 44px;display:flex;justify-content:space-between"><span>Alpha Direct Insurance Company (Pty) Ltd &middot; Licensed by NBFIRA</span><span>Q-2026-00072 &middot; Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>'});
await b.close(); console.log('shot + pdf done');
