import { chromium } from 'playwright';
const url='file:///C:/Users/PRATHA~1/AppData/Local/Temp/claude/C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye/e8239cc9-10b0-4741-938a-19aa627e1b6a/scratchpad/quote_qc2.html';
const out='C:/Users/PRATHA~1/AppData/Local/Temp/claude/C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye/e8239cc9-10b0-4741-938a-19aa627e1b6a/scratchpad/Alpha_Direct_Sample_Quotation.pdf';
let b; try{b=await chromium.launch();}catch(e){b=await chromium.launch({channel:'chrome'});}
const p=await b.newPage();
await p.goto(url,{waitUntil:'load'});
await p.pdf({path:out, format:'A4', printBackground:true, margin:{top:'0',bottom:'14mm',left:'0',right:'0'},
  displayHeaderFooter:true,
  footerTemplate:'<div style="width:100%;font-family:Arial;font-size:8px;color:#6B7280;padding:0 44px;display:flex;justify-content:space-between"><span>Alpha Direct Insurance Company (Pty) Ltd &middot; Licensed by NBFIRA</span><span>Q-2026-00061 &middot; Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>',
  headerTemplate:'<div></div>'});
await b.close(); console.log('PDF ->', out);
