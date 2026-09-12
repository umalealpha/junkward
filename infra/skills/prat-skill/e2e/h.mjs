import { chromium } from 'playwright';
let b; try{b=await chromium.launch();}catch(e){b=await chromium.launch({channel:'chrome'});}
const p=await b.newPage({viewport:{width:794,height:1123}});
await p.goto('file:///C:/Users/PRATHA~1/AppData/Local/Temp/claude/C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye/e8239cc9-10b0-4741-938a-19aa627e1b6a/scratchpad/quote_big.html',{waitUntil:'load'});
const h=await p.evaluate(()=>document.querySelector('.page').getBoundingClientRect().height);
// printable height per A4 page at 96dpi minus the 14mm bottom margin (~53px)
console.log('content height px:', Math.round(h), '| pages needed:', (h/(1123-53)).toFixed(2));
await b.close();
