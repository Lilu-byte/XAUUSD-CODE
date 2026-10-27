// node extract.js -> en_src/<group>.tsv  (key \t persian) for strings with Persian letters, grouped for translation
const fs = require('fs'), vm = require('vm'), { LETTERS, enKey, enVisit } = require('./en_walk.js');
const D = '../app/', files = ['c0.js','c1.js','c2.js','ck.js','c3.js','c4.js','c5.js','c6.js','c7.js', ...fs.readdirSync(D + 'simple').sort().map(f => 'simple/' + f)];
const code = files.map(f => fs.readFileSync(D + f, 'utf8')).join('\n') + '\n;({UNITS, CASES, TERMS, STAGES, FINAL_TASKS, KH_REFS, SIMPLE})';
const G = vm.runInNewContext(code, {});
const seen = new Map(), groups = {};
function take(group, obj) { enVisit(obj, s => { if (!LETTERS.test(s)) return; const k = enKey(s); if (seen.has(k)) { if (seen.get(k) !== s) throw new Error('collision ' + k); return; } seen.set(k, s); (groups[group] = groups[group] || []).push([k, s]); }); }
G.UNITS.forEach(u => take(u.id, u));
const unitOfLesson = {}; G.UNITS.forEach(u => u.lessons.forEach(l => { unitOfLesson[l.id] = u.id; }));
Object.keys(G.SIMPLE).forEach(id => take('simple_' + unitOfLesson[id], G.SIMPLE[id]));
take('cases', G.CASES); take('terms', G.TERMS); take('stages', [G.STAGES, G.FINAL_TASKS]); take('refs', G.KH_REFS);
fs.mkdirSync('en_src', { recursive: true });
let tot = 0;
for (const [g, rows] of Object.entries(groups)) { const chars = rows.reduce((a, r) => a + r[1].length, 0); tot += chars; fs.writeFileSync('en_src/' + g + '.tsv', rows.map(r => r[0] + '\t' + r[1].replace(/\n/g, '\\n')).join('\n') + '\n'); console.log(g.padEnd(14), String(rows.length).padStart(5), String(chars).padStart(7)); }
console.log('total strings', seen.size, 'chars', tot);
