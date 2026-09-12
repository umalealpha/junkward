import { chromium } from 'playwright';
const base='file:///C:/Users/PRATHA~1/AppData/Local/Temp/claude/C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye/e8239cc9-10b0-4741-938a-19aa627e1b6a/scratchpad/';
let b; try{b=await chromium.launch();}catch(e){b=await chromium.launch({channel:'chrome'});}
for (const s of ['detailed','simple']){
  const p=await b.newPage({viewport:{width:794,height:1123},deviceScaleFactor:1.4});
  await p.goto(base+`q_${s}.html`,{waitUntil:'load'});
  const h=await p.evaluate(()=>Math.round(document.querySelector('.page').getBoundingClientRect().height));
  await p.screenshot({path:`dpo-out/q_${s}.png`,fullPage:true});
  const pdf=await p.pdf({format:'A4',printBackground:true,margin:{top:'0',bottom:'15mm',left:'0',right:'0'},displayHeaderFooter:true,headerTemplate:'<div></div>',footerTemplate:'<div style="font-size:8px"></div>'});
  const pages=(pdf.toString('latin1').match(/\/Type \/Page[^s]/g)||[]).length;
  console.log(`${s.padEnd(9)} height ${h}px  ~pages ${pages}`);
  await p.close();
}
await b.close();
