import { chromium } from 'playwright';
let b; try{b=await chromium.launch();}catch(e){b=await chromium.launch({channel:'chrome'});}
const p=await b.newPage({viewport:{width:794,height:1123}});
await p.goto('file:///C:/Users/PRATHA~1/AppData/Local/Temp/claude/C--Users-PrathapAsus-OneDrive---Alpha-Direct-Insurance-Gods-Eye/e8239cc9-10b0-4741-938a-19aa627e1b6a/scratchpad/quote_big.html',{waitUntil:'load'});
const r=await p.evaluate(()=>{
  const out={};
  out.total=Math.round(document.querySelector('.page').getBoundingClientRect().height);
  for (const s of ['table.subtot','.premium','.bank','.payblock','.sign','.foot']){
    const el=document.querySelector(s); if(el){const b=el.getBoundingClientRect(); out[s]=[Math.round(b.top),Math.round(b.bottom)];}
  }
  return out;
});
const per=1123-53;
console.log('content height', r.total, '| pages needed', (r.total/per).toFixed(2));
for (const [k,v] of Object.entries(r)) if(Array.isArray(v)) console.log(`${k.padEnd(14)} ${String(v[0]).padStart(5)}-${String(v[1]).padStart(5)}  (page ${Math.floor(v[0]/per)+1} -> ${Math.floor(v[1]/per)+1})`);
await b.close();
