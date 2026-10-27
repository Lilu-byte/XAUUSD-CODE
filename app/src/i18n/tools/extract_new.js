// node extract_new.js <group> -> en_src/<group>.tsv: only the Persian strings that have no English yet (en/content.json).
// Use this for new content; extract.js regenerates every group and would break the index alignment of en/ct/*.tsv.
const fs = require('fs'), vm = require('vm'), { LETTERS, enKey, enVisit } = require('./en_walk.js');
const g = process.argv[2]; if (!g) throw new Error('usage: node extract_new.js <group>');
const D = '../app/', files = ['c0.js','c1.js','c2.js','ck.js','c3.js','c4.js','c5.js','c6.js','c7.js','v2_h12.js', ...fs.readdirSync(D + 'simple').sort().map(f => 'simple/' + f)];
const code = files.map(f => fs.readFileSync(D + f, 'utf8')).join('\n') + '\n;({UNITS, CASES, TERMS, STAGES, FINAL_TASKS, KH_REFS, SIMPLE, PRACTICE_KIT})';
const G = vm.runInNewContext(code, {});
const have = JSON.parse(fs.readFileSync('../en/content.json', 'utf8'));
if (fs.existsSync('en_src/' + g + '.tsv')) throw new Error('en_src/' + g + '.tsv exists; pick a new group name');
const seen = new Set(), rows = [];
const roots = [G.UNITS, G.CASES, G.TERMS, [G.STAGES, G.FINAL_TASKS], G.KH_REFS, G.PRACTICE_KIT];
roots.forEach(r => enVisit(r, s => { if (!LETTERS.test(s)) return; const k = enKey(s); if (have[k] !== undefined || seen.has(k)) return; seen.add(k); rows.push([k, s]); }));
fs.writeFileSync('en_src/' + g + '.tsv', rows.map(r => r[0] + '\t' + r[1].replace(/\n/g, '\\n')).join('\n') + '\n');
console.log(g, rows.length, 'new strings', rows.reduce((a, r) => a + r[1].length, 0), 'chars');
