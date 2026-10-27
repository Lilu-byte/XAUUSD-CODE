// Rewrites Persian UI text in app.js into t("…") / tr("… {0} …", expr) calls and lists the keys to translate.
// usage: node xf_ui.js in.js out.js keys.tsv
const acorn = require('acorn'), walk = require('acorn-walk'), fs = require('fs');
const [, , IN, OUT, KEYS] = process.argv;
const src = fs.readFileSync(IN, 'utf8');
const ast = acorn.parse(src, { ecmaVersion: 2022, sourceType: 'script', locations: true });
const P = /[؀-ۿ]/;
const SKIP_VAL = new Set(['۰۱۲۳۴۵۶۷۸۹', '٬', '٫', '٠١٢٣٤٥٦٧٨٩']);
const edits = [], keys = new Map(), warns = [];
const lineOf = pos => src.slice(0, pos).split('\n').length;
function addKey(k, pos) { if (!keys.has(k)) keys.set(k, { line: lineOf(pos), n: 0 }); keys.get(k).n++; }
// parent tracking
const parents = new Map();
(function mark(n, p) { if (!n || typeof n.type !== 'string') return; parents.set(n, p); for (const k in n) { const v = n[k]; if (k === 'loc') continue; if (Array.isArray(v)) v.forEach(c => c && typeof c.type === 'string' && mark(c, n)); else if (v && typeof v.type === 'string') mark(v, n); } })(ast, null);
function xf(s, e) { // transformed source of [s,e)
  const inner = edits.filter(x => x.s >= s && x.e <= e && !(x.s === s && x.e === e)).sort((a, b) => a.s - b.s || b.e - a.e);
  let out = '', pos = s;
  for (const x of inner) { if (x.s < pos) continue; out += src.slice(pos, x.s) + x.build(); pos = x.e; }
  return out + src.slice(pos, e);
}
walk.full(ast, n => {
  if (n.type === 'Literal' && typeof n.value === 'string' && P.test(n.value)) {
    const p = parents.get(n);
    if (SKIP_VAL.has(n.value)) return;
    if (p && ((p.type === 'Property' && p.key === n && !p.computed) || p.type === 'SwitchCase' || (p.type === 'BinaryExpression' && /[=!]==?/.test(p.operator)))) { warns.push(['skip-lit', lineOf(n.start), n.value]); return; }
    if (p && p.type === 'CallExpression' && p.callee.type === 'MemberExpression' && /^(includes|split|indexOf|startsWith|endsWith|replace|test|match)$/.test(p.callee.property.name)) { warns.push(['skip-arg', lineOf(n.start), n.value]); return; }
    addKey(n.value, n.start);
    edits.push({ s: n.start, e: n.end, build: () => 'tx(' + src.slice(n.start, n.end) + ')' });
  }
  if (n.type === 'TemplateLiteral' && n.quasis.some(q => P.test(q.value.raw))) unitsOf(n);
});
function simple(ex) { const t = src.slice(ex.start, ex.end); return !/[`<]/.test(t); }
function unitsOf(T) {
  // walk quasis with an HTML state machine; collect units
  let state = 'TEXT', quote = null, unit = null;
  const flush = () => {
    if (!unit) return;
    const parts = unit.parts; // {k:'t', s, e} | {k:'x', node}
    // trim whitespace at ends (text parts only)
    while (parts.length && parts[0].k === 't') { const p = parts[0]; const txt = src.slice(p.s, p.e); const m = txt.match(/^\s*/)[0].length; if (m === txt.length) { parts.shift(); continue; } p.s += m; break; }
    while (parts.length && parts[parts.length - 1].k === 't') { const p = parts[parts.length - 1]; const txt = src.slice(p.s, p.e); const m = txt.match(/\s*$/)[0].length; if (m === txt.length) { parts.pop(); continue; } p.e -= m; break; }
    unit = null;
    if (!parts.length || !parts.some(p => p.k === 't' && P.test(src.slice(p.s, p.e)))) return;
    const s = parts[0].s, e = parts[parts.length - 1].e;
    let key = '', xs = [];
    for (const p of parts) { if (p.k === 't') key += src.slice(p.s, p.e); else { key += '{' + xs.length + '}'; xs.push(p.node); } }
    if (/\\/.test(key)) { warns.push(['backslash', lineOf(s), key]); return; }
    addKey(key, s);
    edits.push({ s, e, build: () => '${' + (xs.length ? 'trx(' + JSON.stringify(key) + ', ' + xs.map(x => xf(x.start, x.end)).join(', ') + ')' : 'tx(' + JSON.stringify(key) + ')') + '}' });
  };
  T.quasis.forEach((q, qi) => {
    const qs = q.start, raw = q.value.raw;
    let i = 0;
    while (i < raw.length) {
      const c = raw[i], pos = qs + i;
      if (state === 'TEXT') {
        if (c === '<') { flush(); state = 'TAG'; i++; continue; }
        if (!unit) unit = { parts: [] };
        const last = unit.parts[unit.parts.length - 1];
        if (last && last.k === 't' && last.e === pos) last.e++; else unit.parts.push({ k: 't', s: pos, e: pos + 1 });
      } else if (state === 'TAG') {
        if (c === '>') state = 'TEXT';
        else if (c === '"' || c === "'") { state = 'ATTR'; quote = c; }
      } else if (state === 'ATTR') {
        if (c === quote) { flush(); state = 'TAG'; }
        else { if (!unit) unit = { parts: [] }; const last = unit.parts[unit.parts.length - 1]; if (last && last.k === 't' && last.e === pos) last.e++; else unit.parts.push({ k: 't', s: pos, e: pos + 1 }); }
      }
      i++;
    }
    const ex = T.expressions[qi];
    if (ex) {
      if ((state === 'TEXT' || state === 'ATTR') && simple(ex)) { if (!unit) unit = { parts: [] }; unit.parts.push({ k: 'x', node: ex, s: src.lastIndexOf('${', ex.start), e: src.indexOf('}', ex.end) + 1 }); }
      else flush();
    }
  });
  flush();
}
const out = xf(0, src.length);
fs.writeFileSync(OUT, out);
const lines = src.split('\n');
fs.writeFileSync(KEYS, [...keys].map(([k, v], i) => [i, v.line, JSON.stringify(k), lines[v.line - 1].trim().slice(0, 160)].join('\t')).join('\n') + '\n');
console.error('keys', keys.size, 'edits', edits.length); warns.forEach(w => console.error(w.join('\t')));
