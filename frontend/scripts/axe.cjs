const {chromium}=require('playwright');const fs=require('fs');
const axe=fs.readFileSync('node_modules/axe-core/axe.min.js','utf8');
(async()=>{const b=await chromium.launch();
for(const w of [1280,390]){const pg=await b.newPage({viewport:{width:w,height:900}});
for(const r of ['/','/app','/app/fix-review','/app/agent-test','/app/report']){
await pg.goto('http://localhost:3100'+r,{waitUntil:'load'});await pg.evaluate(axe);
const res=await pg.evaluate(()=>axe.run());
console.log(w,r,res.violations.map(v=>v.id+':'+v.nodes.length+' '+v.nodes[0].target).join(' | ')||'clean');}}
await b.close()})();
