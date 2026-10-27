const acorn=require('acorn'), walk=require('acorn-walk'), fs=require('fs');
const src=fs.readFileSync(process.argv[2],'utf8');
const ast=acorn.parse(src,{ecmaVersion:2022,sourceType:'script',locations:true});
const P=/[؀-ۿ]/; const out=[];
walk.full(ast,n=>{
  if(n.type==='Literal'&&typeof n.value==='string'&&P.test(n.value)) out.push(['L',n.loc.start.line,n.value]);
  if(n.type==='Literal'&&n.regex&&P.test(n.raw)) out.push(['R',n.loc.start.line,n.raw]);
  if(n.type==='TemplateElement'&&P.test(n.value.raw)) out.push(['T',n.loc.start.line,n.value.raw]);
});
out.sort((a,b)=>a[1]-b[1]);
for(const o of out) console.log(o[0]+'\t'+o[1]+'\t'+o[2].replace(/\n/g,'\\n'));
