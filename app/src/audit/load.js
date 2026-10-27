// load content files into a sandbox and export UNITS, SIMPLE, CASES, TERMS
const fs=require('fs'), vm=require('vm');
const D=require('path').join(__dirname,'..')+'/';
const files=['c0.js','c1.js','c2.js','ck.js','c3.js','c4.js','c5.js','c6.js','c7.js','v2_h12.js',...fs.readdirSync(D+'simple').sort().map(f=>'simple/'+f)];
const src=files.map(f=>fs.readFileSync(D+f,'utf8')).join('\n;\n')+'\n;({UNITS,SIMPLE,PRACTICE_KIT,CASES:typeof CASES!=="undefined"?CASES:[],TERMS:typeof TERMS!=="undefined"?TERMS:[]})';
module.exports=vm.runInNewContext(src,{console});
