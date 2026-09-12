import { chromium } from 'playwright';
let b; try{b=await chromium.launch();}catch(e){b=await chromium.launch({channel:'chrome'});}
const p=await b.newPage({viewport:{width:794,height:1123}});
await p.goto('file:///C:/Users/PRATHA~1/AppData/Local/Temp/claude/C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye/e8239cc9-10b0-4741-938a-19aa627e1b6a/scratchpad/quote_big.html',{waitUntil:'load'});
const info=await p.evaluate(()=>{
  const out=[];
  for (const sel of ['.masthead','.doc-title','table.cover','table.subtot','.premium','.bank','.block.conditions','.sign','.foot']){
    document.querySelectorAll(sel).forEach(el=>{const r=el.getBoundingClientRect();out.push([sel, Math.round(r.top), Math.round(r.bottom)]);});
  }
  return {total: Math.round(document.querySelector('.page').getBoundingClientRect().height), blocks: out};
});
console.log('total', info.total);
for(const [s,t,bm] of info.blocks) console.log(`${s.padEnd(22)} top ${String(t).padStart(5)}  bottom ${String(bm).padStart(5)}`);
await b.close();
