// ---------- data ----------
const RAW = JSON.parse(document.getElementById('gold-data').textContent);
const TFMIN = { D1: 1440, H4: 240, H1: 60, M15: 15, M5: 5 };
const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
const B64I = {}; [...B64].forEach((ch, i) => B64I[ch] = i);
function vdec(str) {
  const out = []; let z = 0, sh = 0;
  for (let i = 0; i < str.length; i++) {
    const b = B64I[str[i]];
    z += (b & 31) * Math.pow(2, sh);
    if (b & 32) { sh += 5; continue; }
    out.push(z % 2 ? -(z + 1) / 2 : z / 2); z = 0; sh = 0;
  }
  return out;
}
const SEGS = RAW.segs.map(s => ({ meta: s, bars: null }));
function seg(i) {
  const S = SEGS[i];
  if (S.bars) return S.bars;
  const m = S.meta, v = vdec(m.b), dt = vdec(m.dt), n = v.length / 4;
  const O = new Float64Array(n), H = new Float64Array(n), L = new Float64Array(n), C = new Float64Array(n), T = new Float64Array(n);
  let pc = m.p0, t = m.t0;
  for (let k = 0; k < n; k++) {
    const o = pc + v[4 * k], c = o + v[4 * k + 3];
    O[k] = o * m.u; C[k] = c * m.u; H[k] = (Math.max(o, c) + v[4 * k + 1]) * m.u; L[k] = (Math.min(o, c) - v[4 * k + 2]) * m.u;
    if (k > 0) t += (dt[k - 1] + 1) * TFMIN[m.tf];
    T[k] = t; pc = c;
  }
  return (S.bars = { O, H, L, C, T, n, tf: m.tf });
}
const ITEMS = RAW.items;
const STATS = RAW.stats;
const byKind = {};
ITEMS.forEach((it, i) => { it.id = i; (byKind[it.k] = byKind[it.k] || []).push(it); });
const PRACTICE_KINDS = ORDER.filter(k => byKind[k] && byKind[k].length);

// ---------- helpers ----------
const $ = (sel, el = document) => el.querySelector(sel);
const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') e.className = v; else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'html') e.innerHTML = v; else if (v !== false && v != null) e.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null) e.append(k.nodeType ? k : document.createTextNode(k));
  return e;
};
const rnd = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
const pick = arr => arr[Math.floor(Math.random() * arr.length)];
const shuffle = arr => { for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [arr[i], arr[j]] = [arr[j], arr[i]]; } return arr; };
const money = p => '$' + p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pct = x => Math.round(x * 100) + '%';
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
function fmtTime(min, tf) {
  const d = new Date(min * 60000);
  const ds = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  if (tf === 'D1') return ds;
  return ds + ' ' + d.toISOString().slice(11, 16);
}
const TFNAME = { D1: 'Daily', H4: '4-hour', H1: '1-hour', M15: '15-minute', M5: '5-minute' };

// ---------- saved progress (this browser only) ----------
const KEY = 'gold-pattern-trainer.v1';
let SAVE = { kinds: {}, modes: {}, settings: {} };
try { const s = JSON.parse(localStorage.getItem(KEY) || 'null'); if (s) SAVE = Object.assign(SAVE, s); } catch (e) {}
function persist() { try { localStorage.setItem(KEY, JSON.stringify(SAVE)); } catch (e) {} }
function record(kind, mode, score) {
  const k = SAVE.kinds[kind] = SAVE.kinds[kind] || { a: 0, c: 0 };
  k.a++; k.c += score;
  const m = SAVE.modes[mode] = SAVE.modes[mode] || { a: 0, c: 0 };
  m.a++; m.c += score;
  // spaced review: right answers push the next review further away, wrong ones bring it back now
  SAVE.box = SAVE.box || {};
  const bx = SAVE.box[kind] || { b: 1, due: 0 };
  bx.b = score >= 1 ? Math.min(5, bx.b + 1) : 1;
  bx.due = Date.now() + [0, 0, 1, 3, 7, 21][bx.b] * 86400000;
  SAVE.box[kind] = bx;
  persist();
}
function dueKinds() {
  const now = Date.now(), B = SAVE.box || {};
  return PRACTICE_KINDS.filter(k => B[k] && B[k].due <= now && (SAVE.kinds[k] || {}).a);
}
function level(kind) {
  const k = SAVE.kinds[kind];
  if (!k || !k.a) return { stars: 0, label: 'New' };
  const acc = k.c / k.a;
  if (k.a >= 8 && acc >= 0.8) return { stars: 3, label: 'Mastered' };
  if (k.a >= 4 && acc >= 0.6) return { stars: 2, label: 'Solid' };
  return { stars: 1, label: 'Learning' };
}
const starText = n => '★'.repeat(n) + '☆'.repeat(3 - n);

// ---------- mirror (flip the chart upside down) ----------
const mkind = (k, m) => m ? (MIRROR_KIND[k] || k) : k;
const MLAB = { Top: 'Bottom', Bottom: 'Top', High: 'Low', Low: 'High', 'Pole top': 'Pole bottom', 'Pole bottom': 'Pole top', 'Cup bottom': 'Cup top', 'Cup top': 'Cup bottom' };
const mlab = (t, m) => !m ? t : (MLAB[t] || t.replace(/^(Top|Bottom)/, w => MLAB[w]));

// ---------- schematic drawings ----------
function svgDraw(d, opts = {}) {
  // opts.step: index into opts.steps for a partial build; undefined = full drawing
  const ns = 'http://www.w3.org/2000/svg', steps = opts.steps;
  const full = !steps || opts.step == null || opts.step >= steps.length;
  const st = full ? null : steps[opts.step];
  const main = (d.paths || [])[0] || [], extra = (d.paths || []).slice(1);
  // bounds from everything, so the frame stays still while it builds
  const ys = [...(d.paths || []).flat().map(p => p[1]), ...(d.lines || []).flatMap(l => [l[1], l[3]]),
    ...(d.labels || []).map(l => l[1]), ...(d.target ? [d.target[1], d.target[3]] : []), ...(d.hb ? [d.hb[1], d.hb[2]] : [])];
  const ymin = Math.min(...ys) - 12, ymax = Math.max(...ys) + 14;
  const W = 200, sc = 1.0, H = Math.max(100, (ymax - ymin) * sc);
  const X = x => 10 + x * 1.8, Y = y => (ymax - y) * sc * (H / ((ymax - ymin) * sc));
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H.toFixed(1)}`); svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', opts.label || 'pattern drawing');
  const add = (tag, at, txt) => { const e = document.createElementNS(ns, tag); for (const k in at) e.setAttribute(k, at[k]); if (txt) e.textContent = txt; svg.append(e); return e; };
  const font = 'IBM Plex Sans, sans-serif';
  const nPts = full ? main.length : Math.min(main.length, st[0]);
  const nLines = full ? (d.lines || []).length : st[1];
  const lastX = nPts ? main[nPts - 1][0] : 0;
  const lines = (d.lines || []).slice(0, nLines);
  for (const ln of lines)
    add('line', { x1: X(ln[0]), y1: Y(ln[1]), x2: X(ln[2]), y2: Y(ln[3]), stroke: 'var(--gold)', 'stroke-width': 1.5, 'stroke-dasharray': '4 3', fill: 'none' });
  const arrow = (x, y1, y2, color, label, side) => {
    add('line', { x1: X(x), y1: Y(y1), x2: X(x), y2: Y(y2), stroke: color, 'stroke-width': 1.2 });
    const dn = y2 < y1 ? -1 : 1;
    add('path', { d: `M${X(x) - 3} ${Y(y2) + 5 * dn} L${X(x)} ${Y(y2)} L${X(x) + 3} ${Y(y2) + 5 * dn}`, stroke: color, fill: 'none', 'stroke-width': 1.2 });
    if (label && opts.labels !== false) add('text', { x: X(x) + (side < 0 ? -5 : 5), y: Y((y1 + y2) / 2) + 3, 'text-anchor': side < 0 ? 'end' : 'start', 'font-size': 7.5, fill: color, 'font-family': font }, label);
  };
  if (full && d.hb) {
    const [x, a, b] = d.hb;
    add('line', { x1: X(x) - 3, y1: Y(a), x2: X(x) + 3, y2: Y(a), stroke: 'var(--sel-line)', 'stroke-width': 1.2 });
    add('line', { x1: X(x) - 3, y1: Y(b), x2: X(x) + 3, y2: Y(b), stroke: 'var(--sel-line)', 'stroke-width': 1.2 });
    add('line', { x1: X(x), y1: Y(a), x2: X(x), y2: Y(b), stroke: 'var(--sel-line)', 'stroke-width': 1.2, 'stroke-dasharray': '2 2' });
    if (opts.labels !== false) add('text', { x: X(x) - 5, y: Y((a + b) / 2) + 3, 'text-anchor': 'end', 'font-size': 7.5, fill: 'var(--sel-line)', 'font-family': font }, 'height');
  }
  if (full && d.target) arrow(d.target[0], d.target[1], d.target[3], d.hb ? 'var(--sel-line)' : 'var(--muted)', d.hb ? 'same height' : '', d.target[0] > 80 ? -1 : 1);
  const pts = main.slice(0, nPts);
  if (pts.length > 1) {
    const body = full && pts.length > 2 ? pts.slice(0, -1) : pts;
    add('polyline', { points: body.map(([x, y]) => `${X(x)},${Y(y)}`).join(' '), fill: 'none', stroke: 'var(--ink)', 'stroke-width': 2.2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
    if (full && pts.length > 2) {
      const a = pts[pts.length - 2], b = pts[pts.length - 1];
      add('polyline', { points: `${X(a[0])},${Y(a[1])} ${X(b[0])},${Y(b[1])}`, fill: 'none', stroke: b[1] > a[1] ? 'var(--up)' : 'var(--down)', 'stroke-width': 2.6, 'stroke-linecap': 'round' });
    }
    if (!full) { const p = pts[pts.length - 1]; add('circle', { cx: X(p[0]), cy: Y(p[1]), r: 3, fill: 'var(--gold)' }); }
  }
  if (full) extra.forEach((p, i) => add('polyline', { points: p.map(([x, y]) => `${X(x)},${Y(y)}`).join(' '), fill: 'none',
    stroke: p[p.length - 1][1] > p[0][1] ? 'var(--up)' : 'var(--down)', 'stroke-width': 2.2, 'stroke-dasharray': (d.dashed || []).includes(i + 1) ? '3 4' : 'none', 'stroke-linecap': 'round' }));
  if (opts.labels !== false) {
    for (const [x, y, t, pos] of d.labels || []) if (full || x <= lastX + 0.01)
      add('text', { x: X(x), y: pos === 'b' ? Y(y) + 13 : Y(y) - 6, 'text-anchor': 'middle', 'font-size': 8.5, fill: 'var(--ink)', 'font-family': font, 'font-weight': 500 }, t);
    for (const ln of lines) if (ln[4])
      add('text', { x: X(ln[2]), y: Y(ln[3]) + (ln[3] > ln[1] ? -5 : 11), 'text-anchor': 'end', 'font-size': 8, fill: 'var(--gold)', 'font-family': font }, ln[4]);
  }
  return svg;
}

// step-by-step lesson drawing with back / next controls
function stepper(P) {
  const steps = P.steps || [];
  const caps = steps.map(s => s[2]);
  const hasT = !!(P.draw.target || P.draw.hb);
  const total = steps.length + 1;
  let i = steps.length ? 0 : total - 1;
  const box = h('div', { class: 'stepper' });
  const fig = h('div', { class: 'stepfig' }), cap = h('p', { class: 'stepcap', 'aria-live': 'polite' }), count = h('span', { class: 'eyebrow' });
  const back = h('button', { class: 'btn', onclick: () => { if (i > 0) { i--; paint(); } } }, '◀ Back');
  const next = h('button', { class: 'btn primary', onclick: () => { if (i < total - 1) { i++; paint(); } } }, 'Next step ▶');
  const all = h('button', { class: 'btn', onclick: () => { i = i === total - 1 ? 0 : total - 1; paint(); } }, '');
  const paint = () => {
    fig.innerHTML = ''; fig.append(svgDraw(P.draw, { steps, step: i, label: P.name }));
    cap.textContent = i < steps.length ? caps[i] : (hasT ? TCAP : 'The finished pattern.');
    count.textContent = steps.length ? `Step ${i + 1} of ${total}` : 'Drawing';
    back.disabled = i === 0; next.disabled = i === total - 1;
    all.textContent = i === total - 1 ? 'Start again' : 'Show finished';
  };
  paint();
  box.append(fig, h('div', { class: 'stepbar' }, count, h('span', { class: 'spacer' }), steps.length ? [back, next, all] : null), cap);
  return box;
}

// ---------- candlestick chart ----------
function makeChart(canvas) {
  const ch = { canvas, cfg: null, map: null };
  ch.draw = (cfg) => {
    if (cfg) ch.cfg = cfg;
    cfg = ch.cfg; if (!cfg) return;
    const B = seg(cfg.seg), dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth, Hh = canvas.clientHeight;
    if (!W) return;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(Hh * dpr);
    const g = canvas.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, Hh);
    const padR = cfg.mirror ? 12 : 66, padB = 24, padT = 12, padL = 6;
    const from = cfg.from, to = cfg.to, nb = to - from + 1 + 3 + (cfg.padBars || 0);
    let lo = Infinity, hi = -Infinity;
    for (let i = from; i <= to; i++) { lo = Math.min(lo, B.L[i]); hi = Math.max(hi, B.H[i]); }
    for (const lv of cfg.levels ? [cfg.levels.st, cfg.levels.tg] : []) { lo = Math.min(lo, lv); hi = Math.max(hi, lv); }
    const pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
    const pw = W - padL - padR, ph = Hh - padT - padB, bw = pw / nb;
    const x = i => padL + (i - from + 0.5) * bw;
    const y = p => cfg.mirror ? padT + (p - lo) / (hi - lo) * ph : padT + (hi - p) / (hi - lo) * ph;
    ch.map = { from, to, x, bw, padL, pw };
    const col = { grid: css('--grid'), muted: css('--muted'), ink: css('--ink'), up: css('--up'), down: css('--down'), gold: css('--gold'),
      sel: css('--sel'), selLine: css('--sel-line'), shade: css('--shade'), good: css('--good'), bad: css('--bad'), panel: css('--panel') };
    g.font = '11px "IBM Plex Mono", ui-monospace, monospace';
    // grid + price axis
    const step = niceStep((hi - lo) / 6);
    g.strokeStyle = col.grid; g.lineWidth = 1; g.fillStyle = col.muted; g.textAlign = 'left'; g.textBaseline = 'middle';
    for (let p = Math.ceil(lo / step) * step; p <= hi; p += step) {
      const yy = Math.round(y(p)) + 0.5; g.beginPath(); g.moveTo(padL, yy); g.lineTo(padL + pw, yy); g.stroke();
      if (!cfg.mirror) g.fillText(p.toFixed(step < 1 ? 2 : step < 10 ? 1 : 0), padL + pw + 6, yy);
    }
    // time axis
    g.textAlign = 'center'; g.textBaseline = 'top';
    const every = Math.max(1, Math.ceil(90 / bw));
    for (let i = from; i <= to; i += every) {
      g.fillStyle = col.muted;
      if (!cfg.hideDates) g.fillText(shortTime(B.T[i], B.tf), x(i), Hh - padB + 6);
      g.strokeStyle = col.grid; g.beginPath(); g.moveTo(Math.round(x(i)) + .5, padT); g.lineTo(Math.round(x(i)) + .5, Hh - padB); g.stroke();
    }
    // shaded answer region / reveal divider
    if (cfg.shade) { g.fillStyle = col.shade; g.fillRect(x(cfg.shade[0]) - bw / 2, padT, (cfg.shade[1] - cfg.shade[0] + 1) * bw, ph); }
    if (cfg.revealFrom != null && cfg.revealFrom <= to) {
      g.fillStyle = col.grid; g.globalAlpha = .5; g.fillRect(x(cfg.revealFrom) - bw / 2, padT, (to - cfg.revealFrom + 1) * bw, ph); g.globalAlpha = 1;
      g.fillStyle = col.muted; g.textAlign = 'left'; g.textBaseline = 'bottom'; g.fillText('what happened next', x(cfg.revealFrom) - bw / 2 + 4, padT + ph - 4);
    }
    // candles
    const cw = Math.max(1, Math.min(14, bw * 0.68));
    for (let i = from; i <= to; i++) {
      const o = B.O[i], c = B.C[i], upc = cfg.mirror ? c < o : c >= o;
      g.strokeStyle = g.fillStyle = upc ? col.up : col.down;
      const xx = Math.round(x(i)) + 0.5;
      g.beginPath(); g.moveTo(xx, y(B.H[i])); g.lineTo(xx, y(B.L[i])); g.stroke();
      const y1 = y(Math.max(o, c)), y2 = y(Math.min(o, c)), top = Math.min(y1, y2);
      g.fillRect(xx - cw / 2, top, cw, Math.max(1, Math.abs(y2 - y1)));
    }
    // selection
    if (cfg.sel) {
      const [a, b] = cfg.sel[0] <= cfg.sel[1] ? cfg.sel : [cfg.sel[1], cfg.sel[0]];
      g.fillStyle = col.sel; g.fillRect(x(a) - bw / 2, padT, (b - a + 1) * bw, ph);
      g.strokeStyle = col.selLine; g.lineWidth = 1.5; g.setLineDash([5, 4]); g.strokeRect(x(a) - bw / 2, padT + .5, (b - a + 1) * bw, ph - 1); g.setLineDash([]);
    }
    if (cfg.pending != null) { g.strokeStyle = col.selLine; g.lineWidth = 2; g.beginPath(); g.moveTo(x(cfg.pending), padT); g.lineTo(x(cfg.pending), padT + ph); g.stroke(); }
    if (cfg.hintZone) {
      const [a0, a1] = cfg.hintZone;
      g.strokeStyle = col.gold; g.lineWidth = 1.5; g.setLineDash([3, 4]); g.strokeRect(x(a0) - bw / 2, padT + 1, (a1 - a0 + 1) * bw, ph - 2); g.setLineDash([]);
      g.fillStyle = col.gold; g.textAlign = 'left'; g.textBaseline = 'top'; g.fillText('look in here', x(a0) - bw / 2 + 4, padT + 4);
    }
    const brkMark = (i, label) => {
      const B2 = B, upB = B2.C[i] >= B2.O[i];
      const yy = cfg.mirror ? (upB ? y(B2.H[i]) + 8 : y(B2.L[i]) - 8) : (upB ? y(B2.L[i]) + 8 : y(B2.H[i]) - 8);
      const dn = (yy > y((B2.H[i] + B2.L[i]) / 2)) ? 1 : -1;
      g.fillStyle = col.selLine; g.beginPath(); g.moveTo(x(i), yy); g.lineTo(x(i) - 6, yy + 9 * dn); g.lineTo(x(i) + 6, yy + 9 * dn); g.closePath(); g.fill();
      g.font = '600 11px "IBM Plex Sans", sans-serif'; g.textAlign = 'center'; g.textBaseline = dn > 0 ? 'top' : 'bottom';
      g.fillText(label, x(i), yy + 11 * dn); g.font = '11px "IBM Plex Mono", ui-monospace, monospace';
    };
    if (cfg.hintBrk != null) brkMark(cfg.hintBrk, 'breakout');
    // overlay pattern geometry
    const ov = cfg.overlay;
    if (ov) {
      g.lineWidth = 2; g.strokeStyle = col.gold;
      for (const [x1, y1, x2, y2] of ov.l) { g.beginPath(); g.moveTo(x(x1), y(y1)); g.lineTo(x(x2), y(y2)); g.stroke(); }
      if (ov.cv) { g.beginPath(); ov.cv.forEach(([i, p], k) => k ? g.lineTo(x(i), y(p)) : g.moveTo(x(i), y(p))); g.stroke(); }
      g.textAlign = 'center';
      const named = ov.p.filter(p => !/^(High|Low)$/.test(p[2]));
      for (const [i, p] of ov.p) { g.fillStyle = col.gold; g.beginPath(); g.arc(x(i), y(p), 3.5, 0, 7); g.fill(); }
      g.font = '600 12px "IBM Plex Sans", sans-serif';
      for (const [i, p, t] of named) {
        const isHigh = cfg.mirror ? false : null;
        const above = labelAbove(B, i, p) !== !!cfg.mirror;
        const ty = above ? y(p) - 16 : y(p) + 6;
        const txt = mlab(t, cfg.mirror), tw = g.measureText(txt).width;
        g.fillStyle = col.panel; g.globalAlpha = .85; g.fillRect(x(i) - tw / 2 - 3, ty - 1, tw + 6, 15); g.globalAlpha = 1;
        g.fillStyle = col.ink; g.textBaseline = 'top'; g.fillText(txt, x(i), ty);
      }
      g.font = '11px "IBM Plex Mono", ui-monospace, monospace';
    }
    // trade levels
    if (cfg.levels) {
      const L0 = cfg.levels, xa = x(L0.from) - bw / 2, xb = padL + pw;
      const lv = [[L0.en, 'entry', col.ink], [L0.st, 'stop', col.bad], [L0.tg, 'target', col.good]];
      g.setLineDash([6, 4]); g.lineWidth = 1.3; g.textAlign = 'left'; g.textBaseline = 'bottom';
      for (const [p, t, c] of lv) { g.strokeStyle = c; g.beginPath(); g.moveTo(xa, y(p)); g.lineTo(xb, y(p)); g.stroke(); g.fillStyle = c; g.fillText(t, xa + 4, y(p) - 2); }
      g.setLineDash([]);
      // measured move arrow from the entry to the target
      const xm = x(L0.from) + bw * 1.5, y0 = y(L0.en), y1 = y(L0.tg), dn = y1 > y0 ? 1 : -1;
      g.strokeStyle = g.fillStyle = col.good; g.lineWidth = 1.6;
      g.beginPath(); g.moveTo(xm, y0); g.lineTo(xm, y1); g.stroke();
      g.beginPath(); g.moveTo(xm, y1); g.lineTo(xm - 5, y1 - 8 * dn); g.lineTo(xm + 5, y1 - 8 * dn); g.closePath(); g.fill();
    }
    if (cfg.marks && cfg.overlay && cfg.overlay.b <= to) brkMark(cfg.overlay.b, 'breakout');
  };
  ch.barAt = (clientX) => {
    if (!ch.map) ch.draw();
    if (!ch.map) return null;
    const r = canvas.getBoundingClientRect(), m = ch.map;
    const i = Math.floor((clientX - r.left - m.padL) / m.bw) + m.from;
    return Math.max(m.from, Math.min(m.to, i));
  };
  return ch;
}
function labelAbove(B, i, p) { return Math.abs(B.H[i] - p) <= Math.abs(B.L[i] - p); }
function niceStep(raw) { const p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p; return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * p; }
function shortTime(min, tf) {
  const d = new Date(min * 60000), mo = d.toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' });
  if (tf === 'D1') return mo + ' ' + String(d.getUTCFullYear()).slice(2);
  if (tf === 'H4' || tf === 'H1') return d.getUTCDate() + ' ' + mo;
  return d.toISOString().slice(11, 16);
}
window.addEventListener('resize', () => charts.forEach(c => c.draw()));
const charts = new Set();
try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => charts.forEach(c => c.draw())); } catch (e) {}

// outcome bar: first bar after confirmation that touched stop or target
function outcomeBar(it) {
  const B = seg(it.g);
  for (let i = it.c + 1; i < B.n && i <= it.c + it.hz; i++) {
    if (it.d === 1 ? (B.L[i] <= it.st || B.H[i] >= it.tg) : (B.H[i] >= it.st || B.L[i] <= it.tg)) return i;
  }
  return null;
}
function outcomeText(it) {
  const ob = outcomeBar(it), B = seg(it.g);
  const shown = ob != null && ob <= it.z;
  const when = ob != null ? ` ${ob - it.c} bar${ob - it.c === 1 ? '' : 's'} later` : '';
  if (it.hit === 1) return { cls: 'good', text: `It worked: price reached the target${when} before the stop. That trade made +${it.R.toFixed(1)}R (R = the amount risked), before costs.`, shown };
  if (it.hit === 0) return { cls: 'bad', text: `It failed: price hit the stop${when} before the target. That trade lost 1R, the full amount risked.`, shown };
  return { cls: 'part', text: `Neither the target nor the stop was hit within ${it.hz} bars. The trade ended at ${it.R >= 0 ? '+' : ''}${it.R.toFixed(1)}R.`, shown: true };
}
function describe(it, mirror) {
  const B = seg(it.g), P = PAT[mkind(it.k, mirror)];
  const named = it.p.filter(p => !/^(High|Low)$/.test(p[2]));
  const parts = [];
  if (named.length) parts.push(named.map(p => `${mlab(p[2], mirror)}${mirror ? '' : ' ' + money(p[1])}`).join(' · '));
  else parts.push(`${it.p.length} swing points touch the two lines`);
  const dir = (it.d === 1) !== !!mirror ? 'up' : 'down';
  const brk = `It broke ${dir} on ${fmtTime(B.T[it.b], B.tf)}${mirror ? '' : ' with a close at ' + money(B.C[it.b])}.`;
  return `${P.name} on the ${TFNAME[B.tf]} chart, ${fmtTime(B.T[it.s], B.tf)} to ${fmtTime(B.T[it.e], B.tf)}. ${parts.join('')}. ${brk}`;
}

// ---------- tabs ----------
const VIEWS = ['learn', 'practice', 'progress', 'works'];
function show(tab) {
  if (!VIEWS.includes(tab)) tab = 'learn';
  VIEWS.forEach(v => { $('#view-' + v).hidden = v !== tab; $('#tab-' + v).setAttribute('aria-selected', v === tab); });
  if (tab === 'progress') renderProgress();
  if (tab === 'practice') { ensurePractice(); charts.forEach(c => c.draw()); }
  if (tab === 'learn') charts.forEach(c => c.draw());
  try { history.replaceState(null, '', '#' + tab); } catch (e) {}
}
document.querySelectorAll('nav.tabs button').forEach(b => b.addEventListener('click', () => {
  if (b.dataset.tab === 'learn' && !$('#view-learn').hidden) { learnDetail = null; learnFilter = 'path'; renderLearn(); }
  show(b.dataset.tab);
}));

// ---------- learn ----------
let learnFilter = 'path';   // 'path' | 'all' | stage id | 'basics' | 'compare'
let learnDetail = null, exampleIdx = 0;
const stageOf = k => STAGES.find(s => s.kinds.includes(k));
function stageProgress(s) {
  if (s.id === 'basics') { const n = PRIMER.filter((p, i) => (SAVE.primer || {})[i]).length; return { done: n, total: PRIMER.length }; }
  const ks = s.kinds.filter(k => PRACTICE_KINDS.includes(k));
  if (!ks.length) return { done: s.kinds.filter(k => (SAVE.read || {})[k]).length, total: s.kinds.length, read: true };
  return { done: ks.filter(k => level(k).stars >= 2).length, total: ks.length };
}
function nextStage() {
  return STAGES.find(s => { const p = stageProgress(s); return p.done < p.total && s.id !== 'rare'; }) || STAGES[1];
}
function goLesson(k) { learnDetail = k; SAVE.read = SAVE.read || {}; SAVE.read[k] = 1; persist(); renderLearn(); window.scrollTo(0, 0); }
function practiseStage(id) { prefs.kind = 'stage:' + id; persistPrefs(); mode = 'find'; startRound(); show('practice'); }

function renderLearn() {
  const v = $('#view-learn'); v.innerHTML = '';
  if (learnDetail) return renderDetail(learnDetail);
  if (learnFilter === 'basics') return renderBasics();
  if (learnFilter === 'compare') return renderCompare();
  const all = STATS._all, ns = nextStage(), due = dueKinds();
  v.append(h('div', { class: 'lead' },
    h('div', { class: 'stack' },
      h('div', { class: 'eyebrow' }, 'XAUUSD · real MT5 history 2004-2026'),
      h('h1', {}, 'Learn every chart pattern, then find it on real gold charts'),
      h('p', { class: 'muted' }, `Follow the path from the basics to the rare patterns. Each lesson builds its pattern step by step, then shows real ones from gold. ${all.n.toLocaleString()} real patterns were found in the gold data; ${ITEMS.length} are used as practice charts.`)),
    h('div', { class: 'stack', style: 'gap:8px' },
      h('button', { class: 'btn primary', onclick: () => { if (ns.id === 'basics') { learnFilter = 'basics'; renderLearn(); } else { learnFilter = ns.id; renderLearn(); } } }, `Continue: ${ns.name}`),
      due.length ? h('button', { class: 'btn', onclick: () => { prefs.kind = 'review'; persistPrefs(); mode = 'name'; startRound(); show('practice'); } }, `Review ${due.length} due pattern${due.length > 1 ? 's' : ''}`) : null)));
  // path
  const path = h('ol', { class: 'path', 'aria-label': 'Learning path' });
  STAGES.forEach((s, i) => {
    const p = stageProgress(s), on = learnFilter === s.id, cur = s.id === ns.id;
    path.append(h('li', {}, h('button', { class: 'stage' + (on ? ' on' : '') + (cur ? ' cur' : ''), 'aria-pressed': on,
      onclick: () => { learnFilter = s.id === 'basics' ? 'basics' : (on ? 'path' : s.id); renderLearn(); } },
      h('span', { class: 'num' }, String(i + 1)),
      h('span', { class: 'sn' }, s.name), h('span', { class: 'sb' }, s.blurb),
      h('span', { class: 'meter' }, h('i', { style: `width:${p.total ? Math.round(p.done / p.total * 100) : 0}%` })),
      h('span', { class: 'sp' }, s.id === 'basics' ? `${p.done}/${p.total} checks` : p.read ? `${p.done}/${p.total} read` : `${p.done}/${p.total} solid`))));
  });
  v.append(path);
  const fl = h('div', { class: 'filters', role: 'group', 'aria-label': 'Show' });
  [['path', 'Everything'], ['compare', 'Look-alikes side by side']].forEach(([k, t]) =>
    fl.append(h('button', { 'aria-pressed': learnFilter === k || (k === 'path' && learnFilter === 'all'), onclick: () => { learnFilter = k; renderLearn(); } }, t)));
  v.append(fl);
  const stg = STAGES.find(s => s.id === learnFilter);
  const groups = stg ? [stg] : STAGES.filter(s => s.id !== 'basics');
  for (const s of groups) {
    const head = h('div', { class: 'grouphead' }, h('h2', {}, s.name), h('span', { class: 'muted' }, s.blurb), h('span', { class: 'spacer' }),
      s.id !== 'rare' ? h('button', { class: 'btn', onclick: () => practiseStage(s.id) }, 'Practise this stage') : null);
    const grid = h('div', { class: 'grid' });
    for (const k of s.kinds) {
      const P = PAT[k], lv = level(k);
      grid.append(h('button', { class: 'card', onclick: () => goLesson(k) },
        h('div', { class: 'cardfig' }, svgDraw(P.draw, { label: P.name, labels: false })),
        h('div', { class: 't' }, h('b', {}, P.name), h('span', { class: 'chip ' + P.cat }, CAT[P.cat])),
        h('div', { class: 's' }, P.what),
        P.learnOnly ? h('div', { class: 'eyebrow' }, (SAVE.read || {})[k] ? 'Read · learn only' : 'Learn only')
          : h('div', { class: 'stars', title: lv.label }, starText(lv.stars) + ' ' + lv.label)));
    }
    v.append(h('section', { class: 'group' }, head, grid));
  }
}

function renderBasics() {
  const v = $('#view-learn');
  SAVE.primer = SAVE.primer || {};
  v.append(h('div', { class: 'row', style: 'margin-bottom:14px' }, h('button', { class: 'btn', onclick: () => { learnFilter = 'path'; renderLearn(); } }, '← Learning path')),
    h('div', { class: 'stack', style: 'margin-bottom:18px' }, h('div', { class: 'eyebrow' }, 'Stage 1'), h('h1', {}, 'Basics'),
      h('p', { class: 'muted' }, 'Seven ideas that every pattern is built from. Answer the quick check under each one.')));
  const list = h('div', { class: 'primer' });
  PRIMER.forEach((c, i) => {
    const box = h('article', { class: 'panel pcard' });
    const fig = c.draw ? h('div', { class: 'pfig' }, svgDraw(c.draw, { label: c.title })) : h('div', { class: 'pfig tfbars' }, tfBars());
    const check = h('div', { class: 'pcheck' });
    const paintCheck = () => {
      check.innerHTML = '';
      check.append(h('b', {}, 'Quick check: '), c.q);
      const opts = h('div', { class: 'row' });
      const order = c._order || (c._order = shuffle(c.options.map((o, j) => j)));
      order.forEach(j => opts.append(h('button', { class: 'btn' + (c._picked === j ? (j === c.a ? ' right' : ' wrong') : (c._picked != null && j === c.a ? ' right' : '')),
        disabled: c._picked != null, onclick: () => { c._picked = j; if (j === c.a) { SAVE.primer[i] = 1; persist(); } paintCheck(); } }, c.options[j])));
      check.append(opts);
      if (c._picked != null) {
        check.append(h('p', { class: c._picked === c.a ? 'pos' : 'neg' }, c._picked === c.a ? 'Right.' : `Not quite. The answer is: ${c.options[c.a]}.`));
        if (c._picked !== c.a) check.append(h('button', { class: 'btn', onclick: () => { c._picked = null; c._order = null; paintCheck(); } }, 'Try again'));
      }
      else if (SAVE.primer[i]) check.append(h('p', { class: 'muted' }, 'You answered this one before.'));
    };
    paintCheck();
    box.append(h('div', { class: 'eyebrow' }, `Idea ${i + 1} of ${PRIMER.length}`), h('h2', {}, c.title), fig, h('p', {}, c.text), check);
    list.append(box);
  });
  v.append(list, h('div', { class: 'row', style: 'margin-top:18px' },
    h('button', { class: 'btn primary', onclick: () => { learnFilter = 'tops'; renderLearn(); window.scrollTo(0, 0); } }, 'Next stage: Tops and bottoms')));
}
function tfBars() {
  // per-timeframe average result vs random entries, from the gold test
  const rows = [['Daily', 0.34, 0.00], ['4-hour', 0.09, 0.03], ['1-hour', 0.18, -0.06], ['15-min', 0.06, -0.07], ['5-min', 0.01, -0.01]];
  const wrap = h('div', { class: 'bars' });
  const max = 0.4;
  for (const [n, a, b] of rows) {
    const w = x => Math.max(0, Math.round(Math.abs(x) / max * 100));
    wrap.append(h('div', { class: 'bar' }, h('span', { class: 'bn' }, n),
      h('span', { class: 'bt' }, h('i', { class: 'pat', style: `width:${w(a)}%` }), h('i', { class: 'rnd', style: `width:${w(b)}%` })),
      h('span', { class: 'bv' }, `${fmtR(a)} vs ${fmtR(b)}`)));
  }
  wrap.append(h('div', { class: 'legend' }, h('span', {}, h('i', { class: 'pat' }), 'patterns'), h('span', {}, h('i', { class: 'rnd' }), 'random entries'), h('span', {}, 'average result per trade after costs')));
  return wrap;
}

function compareCard(a, b, why) {
  return h('article', { class: 'panel cmp' },
    h('div', { class: 'cmpfigs' },
      h('figure', {}, svgDraw(PAT[a].draw, { label: PAT[a].name, labels: false }), h('figcaption', {}, h('button', { class: 'linkbtn', onclick: () => goLesson(a) }, PAT[a].name))),
      h('span', { class: 'vs' }, 'vs'),
      h('figure', {}, svgDraw(PAT[b].draw, { label: PAT[b].name, labels: false }), h('figcaption', {}, h('button', { class: 'linkbtn', onclick: () => goLesson(b) }, PAT[b].name)))),
    h('p', {}, h('b', {}, 'The difference: '), why));
}
function renderCompare() {
  const v = $('#view-learn');
  v.append(h('div', { class: 'row', style: 'margin-bottom:14px' }, h('button', { class: 'btn', onclick: () => { learnFilter = 'path'; renderLearn(); } }, '← Learning path')),
    h('div', { class: 'stack', style: 'margin-bottom:18px' }, h('h1', {}, 'Look-alikes side by side'),
      h('p', { class: 'muted' }, 'These pairs get mixed up the most. Each pair has one thing that tells them apart.')));
  v.append(h('div', { class: 'cmpgrid' }, LOOKALIKES.map(([a, b, why]) => compareCard(a, b, why))));
}

function renderDetail(k) {
  const v = $('#view-learn'), P = PAT[k], st = STATS[k], S = stageOf(k);
  v.innerHTML = '';
  const sib = S ? S.kinds : ORDER, idx = sib.indexOf(k);
  const prev = sib[idx - 1], next = sib[idx + 1];
  v.append(h('div', { class: 'row', style: 'margin-bottom:14px' },
    h('button', { class: 'btn', onclick: () => { learnDetail = null; learnFilter = S ? S.id : 'path'; renderLearn(); } }, '← ' + (S ? S.name : 'All patterns')),
    h('span', { class: 'spacer' }),
    prev ? h('button', { class: 'btn', onclick: () => goLesson(prev) }, '◀ ' + PAT[prev].name) : null,
    next ? h('button', { class: 'btn', onclick: () => goLesson(next) }, PAT[next].name + ' ▶') : null));
  const bias = P.bias === 1 ? 'Bullish (expects a rise)' : P.bias === -1 ? 'Bearish (expects a fall)' : 'Neutral: breaks either way';
  const left = h('div', { class: 'stack' },
    h('div', { class: 'row' }, h('span', { class: 'chip ' + P.cat }, CAT[P.cat]), h('span', { class: 'chip' }, bias)),
    h('h1', {}, P.name),
    h('div', { class: 'panel drawing' }, stepper(P)),
    h('p', {}, P.what), h('p', {}, P.means));
  const right = h('div', { class: 'stack' },
    h('h3', {}, 'Checklist: is it really one?'), h('ul', { class: 'checks' }, P.spot.map(s => h('li', {}, s))),
    h('h3', {}, 'How traders use it'), tradeRow(P),
    h('h3', {}, 'Common mistake'), h('p', {}, P.mistake));
  if (st) right.append(h('div', { class: 'note' },
    `On real gold: ${st.n} found. Reached the target first ${pct(st.target)} of the time, hit the stop first ${pct(st.stop)}. Average result ${fmtR(st.avgR)} per trade after a $0.40 cost, against ${fmtR(st.baseR)} for random entries with the same stop and target.`));
  if (P.learnOnly) right.append(h('div', { class: 'note' }, P.learnOnly));
  v.append(h('div', { class: 'detail' }, left, right));
  const list = byKind[k];
  if (list && list.length) {
    const box = h('div', { class: 'panel', style: 'margin-top:20px' });
    const head = h('div', { class: 'task' }, h('div', { class: 'stack', style: 'gap:2px' }, h('div', { class: 'q' }, 'Real ones on gold'), h('div', { class: 'meta' })),
      h('div', { class: 'row' },
        h('button', { class: 'btn', onclick: () => { exampleIdx++; drawEx(); } }, 'Another real one'),
        h('button', { class: 'btn primary', onclick: () => { prefs.kind = k; persistPrefs(); mode = 'find'; startRound(); show('practice'); } }, 'Practise finding it')));
    const cv = h('canvas', { 'aria-label': 'real gold chart with the pattern marked' });
    const desc = h('div', { class: 'feedback' });
    box.append(head, h('div', { class: 'chartbox' }, cv), chartLegend(), desc);
    v.append(box);
    const chart = makeChart(cv); charts.add(chart);
    exampleIdx = Math.floor(Math.random() * list.length);
    const drawEx = () => {
      const it = list[exampleIdx % list.length], ob = outcomeBar(it);
      const to = Math.min(it.z, Math.max(it.b + 12, (ob || it.b) + 8));
      chart.draw({ seg: it.g, from: Math.max(it.a, it.s - 25), to, overlay: it, shade: [it.s, it.e], marks: true, levels: { en: it.en, st: it.st, tg: it.tg, from: it.c }, revealFrom: it.c + 1 });
      $('.meta', head).textContent = `${TFNAME[seg(it.g).tf]} chart · example ${exampleIdx % list.length + 1} of ${list.length}`;
      const oc = outcomeText(it);
      desc.innerHTML = ''; desc.append(h('p', {}, describe(it, false)), factsRow(it, false), h('p', { class: oc.cls === 'good' ? 'pos' : oc.cls === 'bad' ? 'neg' : '' }, oc.text));
    };
    requestAnimationFrame(drawEx);
  }
  const pairs = LOOKALIKES.filter(l => l[0] === k || l[1] === k);
  if (pairs.length) v.append(h('div', { class: 'stack', style: 'margin-top:24px' }, h('h2', {}, 'Don\'t confuse it with'),
    h('div', { class: 'cmpgrid' }, pairs.map(([a, b, why]) => compareCard(a, b, why)))));
}
function tradeRow(P) {
  // split the trade sentence into entry / stop / target chips where possible
  const parts = P.trade.split(/(?<=\.)\s+/);
  return h('ul', { class: 'trade' }, parts.map(t => {
    const lab = /^(Buy|Sell|Trade|Inside)/.test(t) ? 'Entry' : /^Stop/.test(t) ? 'Stop' : /^Target/.test(t) ? 'Target' : '';
    return h('li', {}, lab ? h('span', { class: 'tl ' + lab.toLowerCase() }, lab) : null, h('span', {}, t));
  }));
}
function chartLegend() {
  return h('div', { class: 'legendrow' },
    h('span', {}, h('i', { class: 'lg gold' }), 'pattern lines'), h('span', {}, h('i', { class: 'lg shade' }), 'pattern area'),
    h('span', {}, h('i', { class: 'lg brk' }), 'breakout candle'), h('span', {}, h('i', { class: 'lg tgt' }), 'target'), h('span', {}, h('i', { class: 'lg stp' }), 'stop'));
}
function factsRow(it, mirror) {
  const B = seg(it.g), bars = it.e - it.s + 1;
  const risk = Math.abs(it.en - it.st), rew = Math.abs(it.tg - it.en);
  const f = [['Lasted', `${bars} candles`], ['Breakout close', mirror ? 'hidden' : money(it.en)], ['Stop', mirror ? 'hidden' : `${money(it.st)} (${money(risk).slice(1)} away)`],
    ['Target', mirror ? 'hidden' : `${money(it.tg)} (${money(rew).slice(1)} away)`], ['Reward : risk', `${(rew / risk).toFixed(1)} : 1`]];
  return h('dl', { class: 'facts' }, f.flatMap(([a, b]) => [h('dt', {}, a), h('dd', {}, b)]));
}
const fmtR = r => { const v = Math.round(r * 100) / 100; return (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(2) + 'R'; };

// ---------- practice ----------
const MODES = {
  find: ['Find it', 'Mark where the pattern is'],
  name: ['Name it', 'Say which pattern is shaded'],
  work: ['Will it work?', 'Target or stop first?']
};
let mode = 'find';
let prefs = Object.assign({ kind: 'auto', tfs: ['D1', 'H4', 'H1', 'M15', 'M5'], mirror: false, blind: true }, SAVE.settings || {});
function persistPrefs() { SAVE.settings = prefs; persist(); }
let round = null, pchart = null, recent = [], session = { a: 0, c: 0 };

function poolFor(kind) {
  const list = (byKind[kind] || []).filter(it => prefs.tfs.includes(seg(it.g).tf));
  return list.length ? list : (byKind[kind] || []);
}
function chooseKind() {
  let ks = PRACTICE_KINDS.filter(k => poolFor(k).length);
  if (prefs.kind.startsWith('stage:')) { const S = STAGES.find(s => 'stage:' + s.id === prefs.kind); if (S) ks = ks.filter(k => S.kinds.includes(k)); }
  else if (prefs.kind === 'review') { const d = dueKinds(); if (d.length) ks = d; }
  else if (prefs.kind !== 'auto' && PAT[prefs.kind]) return prefs.kind;
  if (!ks.length) ks = PRACTICE_KINDS.slice();
  const w = ks.map(k => { const s = SAVE.kinds[k] || { a: 0, c: 0 }; return 1 + 3 * (1 - (s.c + 1) / (s.a + 2)); });
  let r = Math.random() * w.reduce((a, b) => a + b, 0);
  for (let i = 0; i < ks.length; i++) { r -= w[i]; if (r <= 0) return ks[i]; }
  return ks[ks.length - 1];
}
function startRound() {
  let kind = chooseKind(), list = poolFor(kind);
  if (mode === 'work') list = list.filter(it => it.hit !== 0.5);
  let cands = list.filter(it => !recent.includes(it.id));
  if (!cands.length) cands = list;
  const it = pick(cands);
  recent.push(it.id); if (recent.length > 25) recent.shift();
  const span = it.e - it.s, B = seg(it.g);
  const mirror = prefs.mirror && Math.random() < 0.5;
  // window: pattern placed anywhere from the left third to the right edge, never jammed into a corner
  const pw = it.e - it.s + 1;
  const L = Math.max(60, Math.min(260, Math.round(pw * (2.2 + Math.random() * 1.6))));
  const room = Math.max(0, L - pw), edge = Math.round(L * 0.08);
  let lead = Math.round(edge + Math.random() * Math.max(0, room - 2 * edge));   // candles before the pattern
  lead = Math.max(Math.min(edge, room), Math.min(lead, room - Math.min(edge, room)));
  let from = it.s - lead, to = from + L - 1;
  if (to < it.b + 2) { to = it.b + 2; from = to - L + 1; }
  if (to > it.z) { to = it.z; from = Math.max(it.a, to - L + 1); }
  if (from < it.a) { from = it.a; to = Math.min(it.z, from + L - 1); }
  const ob = outcomeBar(it);
  const mid = (it.s + it.e) / 2, zw = Math.max(span * 1.1, 12) + rnd(0, Math.round(span * 0.6));
  const z0 = Math.max(from, Math.round(mid - zw * (0.3 + Math.random() * 0.4)));
  round = { it, mirror, from, to, kind: mkind(it.k, mirror), sel: null, pending: null, done: false, ob, hints: 0, zone: [z0, Math.min(to, Math.round(z0 + zw))],
    revealTo: Math.min(it.z, Math.max(to + 10, (ob || to) + 10)) };
  if (mode === 'work') { round.to = it.c; round.from = Math.max(it.a, Math.min(from, it.s - 5)); }
  if (mode === 'name') round.options = makeOptions(round.kind);
  renderPractice();
}
function makeOptions(k) {
  const group = CONFUSE.find(g => g.includes(k)) || PRACTICE_KINDS;
  const near = shuffle(group.filter(x => x !== k && PRACTICE_KINDS.includes(x))).slice(0, 2);
  const rest = shuffle(PRACTICE_KINDS.filter(x => x !== k && !near.includes(x))).slice(0, 3 - near.length);
  return shuffle([k, ...near, ...rest]);
}
function ensurePractice() { if (!round) startRound(); }

function renderPractice() {
  const v = $('#view-practice'); v.innerHTML = '';
  const mb = h('div', { class: 'modebar', role: 'group', 'aria-label': 'Practice mode' });
  for (const [k, [t, s]] of Object.entries(MODES))
    mb.append(h('button', { 'aria-pressed': mode === k, onclick: () => { mode = k; startRound(); } }, t, h('span', {}, s)));
  v.append(mb);
  const r = round, it = r.it, B = seg(it.g), P = PAT[r.kind];
  const box = h('div', { class: 'panel' });
  let q;
  if (mode === 'find') q = h('div', { class: 'q' }, 'Find the ', h('em', {}, P.name));
  else if (mode === 'name') q = h('div', { class: 'q' }, 'Which pattern is in the shaded area?');
  else q = h('div', { class: 'q' }, h('em', {}, P.name), ' just broke out. Target or stop first?');
  const tfLabel = `${TFNAME[B.tf]} chart`;
  const dateLabel = (!prefs.blind || r.done) ? ` · ${fmtTime(B.T[r.from], B.tf)} to ${fmtTime(B.T[r.to], B.tf)}` : ' · dates hidden';
  box.append(h('div', { class: 'task' }, h('div', { class: 'stack', style: 'gap:2px' }, q,
    h('div', { class: 'meta' }, h('span', {}, 'XAUUSD · ' + tfLabel + dateLabel), r.mirror ? h('span', {}, 'flipped upside down, prices hidden') : null)),
    h('div', { class: 'score' }, `This session ${Math.round(session.c * 100) / 100}/${session.a}`)));
  const cv = h('canvas', { 'aria-label': 'XAUUSD candlestick chart' });
  const cb = h('div', { class: 'chartbox' }, cv);
  if (mode === 'find' && r.hints >= 1 && !r.done) cb.append(h('div', { class: 'hintdraw' }, svgDraw(P.draw, { labels: false, label: P.name })));
  box.append(cb);
  pchart = makeChart(cv); charts.forEach(c => { if (!document.body.contains(c.canvas)) charts.delete(c); }); charts.add(pchart);
  const cfg = () => {
    const c = { seg: it.g, from: r.from, to: r.to, mirror: r.mirror, hideDates: prefs.blind && !r.done };
    if (mode === 'find') { c.sel = r.sel; c.pending = r.pending; if (!r.done) { c.hintZone = r.hints >= 2 ? r.zone : null; c.hintBrk = r.hints >= 3 ? it.b : null; } }
    if (mode === 'name') c.shade = [it.s, it.e];
    if (mode === 'work') { c.overlay = it; c.levels = { en: it.en, st: it.st, tg: it.tg, from: it.c }; if (!r.done) c.padBars = Math.round((r.to - r.from) * 0.25); }
    if (r.done) {
      c.overlay = it; c.marks = true;
      if (mode === 'find') c.shade = [it.s, it.e];
      if (r.revealed) { c.to = r.revealTo; c.revealFrom = r.to + 1; c.levels = { en: it.en, st: it.st, tg: it.tg, from: it.c }; }
    }
    return c;
  };
  pchart.cfg = cfg();
  requestAnimationFrame(() => pchart.draw(cfg()));
  if (mode === 'find' && !r.done) wireSelect(cv, cfg);
  // actions / feedback
  if (mode === 'find' && !r.done) {
    box.append(h('div', { class: 'actions' },
      h('span', { class: 'muted', id: 'sel-status', style: 'font-size:13px' }, selStatus(r)),
      h('span', { class: 'spacer' }),
      h('button', { class: 'btn', disabled: r.hints >= 3, title: 'Each hint lowers the score for this chart', onclick: () => { r.hints++; renderPractice(); } },
        ['Hint 1: the drawing', 'Hint 2: where to look', 'Hint 3: the breakout', 'No more hints'][r.hints]),
      h('button', { class: 'btn', onclick: () => { r.sel = null; r.pending = null; renderPractice(); } }, 'Clear'),
      h('button', { class: 'btn primary', id: 'btn-check', disabled: !selOk(r), onclick: checkFind }, 'Check')));
  }
  if (mode === 'name' && !r.done) {
    box.append(h('div', { class: 'choices' }, r.options.map(k => h('button', { onclick: () => checkName(k) }, PAT[k].name))));
  }
  if (mode === 'work' && !r.done) {
    box.append(h('div', { class: 'choices' },
      h('button', { onclick: () => checkWork(1) }, 'Target first'), h('button', { onclick: () => checkWork(0) }, 'Stop first')),
      h('div', { class: 'actions' }, h('span', { class: 'muted', style: 'font-size:13px' },
        `Entry ${r.mirror ? '' : money(it.en)} at the breakout close. Stop ${r.mirror ? '' : money(it.st)}, target ${r.mirror ? '' : money(it.tg)} (${(Math.abs(it.tg - it.en) / Math.abs(it.en - it.st)).toFixed(1)}× the risk).`)));
  }
  if (r.done) {
    if (mode === 'name') box.append(h('div', { class: 'choices' }, r.options.map(k => h('button', { class: k === r.kind ? 'right' : k === r.answer ? 'wrong' : '', disabled: true }, PAT[k].name))));
    const fbt = h('div', { class: 'stack', style: 'gap:6px;min-width:0' }, h('div', { class: 'verdict ' + r.vcls }, r.verdict));
    const fb = h('div', { class: 'feedback fbgrid' }, h('figure', { class: 'fbfig' }, svgDraw(P.draw, { label: P.name, labels: false }), h('figcaption', {}, 'The textbook shape')), fbt);
    if (r.extra) fbt.append(h('p', {}, r.extra));
    fbt.append(h('p', {}, describe(it, r.mirror)), factsRow(it, r.mirror));
    if (mode !== 'work') fbt.append(h('div', {}, h('b', {}, 'What makes it one'), h('ul', { class: 'checks' }, P.spot.map(s => h('li', {}, s)))));
    if (mode === 'name' && r.answer !== r.kind) {
      const la = lookalikeFor(r.answer, r.kind);
      fbt.append(compareCard(r.answer, r.kind, la ? la[2] : `${PAT[r.answer].name}: ${PAT[r.answer].what} ${PAT[r.kind].name}: ${PAT[r.kind].what}`));
    }
    if (r.revealed || mode === 'work') { const oc = outcomeText(it); fbt.append(h('p', { class: oc.cls === 'good' ? 'pos' : oc.cls === 'bad' ? 'neg' : '' }, oc.text + (oc.shown ? '' : ' (That happened after the part of the chart shown here.)'))); }
    box.append(chartLegend(), fb);
    box.append(h('div', { class: 'actions' },
      !r.revealed ? h('button', { class: 'btn', onclick: () => { r.revealed = true; renderPractice(); } }, 'Show what happened next') : null,
      h('button', { class: 'btn', onclick: () => { learnDetail = r.kind; renderLearn(); show('learn'); } }, 'Open the lesson'),
      h('span', { class: 'spacer' }),
      h('button', { class: 'btn primary', onclick: startRound }, 'Next chart')));
  }
  v.append(box);
  // settings
  const sel = h('select', { id: 'pat-select', onchange: e => { prefs.kind = e.target.value; persistPrefs(); startRound(); } },
    h('option', { value: 'auto' }, 'All patterns (weakest come up more)'),
    h('option', { value: 'review' }, `Review due (${dueKinds().length})`),
    h('optgroup', { label: 'Stages' }, STAGES.filter(s => s.kinds.some(k => PRACTICE_KINDS.includes(k))).map(s => h('option', { value: 'stage:' + s.id }, s.name))),
    h('optgroup', { label: 'One pattern' }, PRACTICE_KINDS.map(k => h('option', { value: k }, PAT[k].name))));
  const tfs = h('span', { class: 'row', style: 'gap:10px' }, 'Timeframes:', Object.keys(TFMIN).map(tf => h('label', {},
    h('input', { type: 'checkbox', id: 'tf-' + tf, checked: prefs.tfs.includes(tf), onchange: e => {
      prefs.tfs = e.target.checked ? [...new Set([...prefs.tfs, tf])] : prefs.tfs.filter(x => x !== tf);
      if (!prefs.tfs.length) prefs.tfs = [tf];
      persistPrefs(); startRound(); } }), tf)));
  v.append(h('div', { class: 'settings' },
    h('label', {}, 'Pattern: ', sel), tfs,
    h('label', {}, h('input', { type: 'checkbox', id: 'opt-blind', checked: prefs.blind, onchange: e => { prefs.blind = e.target.checked; persistPrefs(); renderPractice(); } }), 'Hide dates until answered'),
    h('label', {}, h('input', { type: 'checkbox', id: 'opt-mirror', checked: prefs.mirror, onchange: e => { prefs.mirror = e.target.checked; persistPrefs(); startRound(); } }), 'Sometimes flip charts upside down')));
  if (sel.value !== prefs.kind) sel.value = prefs.kind;
}
function wireSelect(cv, cfg) {
  const r = round; let dragging = false, start = null, moved = false;
  cv.addEventListener('pointerdown', e => { const i = pchart.barAt(e.clientX); if (i == null) return; dragging = true; moved = false; start = i; cv.setPointerCapture(e.pointerId); });
  cv.addEventListener('pointermove', e => {
    if (!dragging) return; const i = pchart.barAt(e.clientX);
    if (i !== start) moved = true;
    if (moved) { r.sel = [start, i]; r.pending = null; pchart.draw(cfg()); }
  });
  cv.addEventListener('pointerup', e => {
    if (!dragging) return; dragging = false; const i = pchart.barAt(e.clientX);
    if (!moved) {
      if (r.pending != null && r.pending !== i) { r.sel = [r.pending, i]; r.pending = null; }
      else { r.pending = i; r.sel = null; }
    }
    pchart.draw(cfg());
    $('#sel-status').textContent = selStatus(r); $('#btn-check').disabled = !selOk(r);
  });
}
const selOk = r => r.sel && Math.abs(r.sel[1] - r.sel[0]) >= 2;
const selStatus = r => r.sel ? `${Math.abs(r.sel[1] - r.sel[0]) + 1} candles marked. Drag again to change it.` : r.pending != null ? 'Now tap the last candle of the pattern.' : 'Drag across the candles where the pattern sits (or tap its first and last candle).';
function iou(a, b) { const s = Math.max(a[0], b[0]), e = Math.min(a[1], b[1]); const inter = Math.max(0, e - s + 1); return inter / (Math.max(a[1], b[1]) - Math.min(a[0], b[0]) + 1); }
function checkFind() {
  const r = round, it = r.it;
  const sel = r.sel[0] <= r.sel[1] ? r.sel : [r.sel[1], r.sel[0]];
  let best = iou(sel, [it.s, it.e]);
  for (const o of RAW.others) if (o[0] === it.k && o[1] === it.g && o[2] >= r.from && o[3] <= r.to) best = Math.max(best, iou(sel, [o[2], o[3]]));
  let score;
  const cap = [1, 0.75, 0.5, 0.5][r.hints];
  if (best >= 0.6) { score = cap; r.verdict = r.hints ? `Found it, with ${r.hints} hint${r.hints > 1 ? 's' : ''}` : 'Found it'; r.vcls = 'good'; }
  else if (best >= 0.35) { score = cap / 2; r.verdict = 'Close: you caught part of it'; r.vcls = 'part'; r.extra = 'The shaded area shows the full pattern, from the start of the move into it to the breakout candle.'; }
  else { score = 0; r.verdict = 'Not quite'; r.vcls = 'bad'; r.extra = 'The shaded area shows where it was.'; }
  r.done = true; session.a++; session.c += score; record(r.kind, 'find', score); renderPractice();
}
function checkName(k) {
  const r = round; r.answer = k; r.done = true;
  const ok = k === r.kind;
  r.verdict = ok ? 'Correct' : `It was a ${PAT[r.kind].name}`; r.vcls = ok ? 'good' : 'bad';
  session.a++; session.c += ok ? 1 : 0; record(r.kind, 'name', ok ? 1 : 0); renderPractice();
}
function checkWork(guess) {
  const r = round, it = r.it; r.done = true; r.revealed = true;
  const ok = guess === it.hit;
  r.verdict = ok ? 'Right call' : 'Wrong call'; r.vcls = ok ? 'good' : 'bad';
  const st = STATS[it.k];
  r.extra = st ? `Across all ${st.n} ${PAT[it.k].name.toLowerCase()} patterns found on gold, the target came first ${pct(st.target)} of the time. Nobody gets this right reliably; the shape alone does not decide it.` : '';
  session.a++; session.c += ok ? 1 : 0;
  const m = SAVE.modes.work = SAVE.modes.work || { a: 0, c: 0 }; m.a++; m.c += ok ? 1 : 0; persist();
  renderPractice();
}

// ---------- progress ----------
function renderProgress() {
  const v = $('#view-progress'); v.innerHTML = '';
  const tried = PRACTICE_KINDS.filter(k => SAVE.kinds[k] && SAVE.kinds[k].a);
  const mastered = PRACTICE_KINDS.filter(k => level(k).stars === 3).length;
  const m = SAVE.modes;
  v.append(h('div', { class: 'stack', style: 'margin-bottom:16px' }, h('div', { class: 'eyebrow' }, 'Saved in this browser only'), h('h1', {}, 'Your progress')));
  const tile = (n, l) => h('div', { class: 'panel' }, h('b', {}, n), h('span', { class: 'muted' }, l));
  const acc = o => o && o.a ? pct(o.c / o.a) : '–';
  v.append(h('div', { class: 'big' },
    tile(`${mastered}/${PRACTICE_KINDS.length}`, 'patterns mastered (8+ tries, 80%+)'),
    tile(acc(m.find), `Find it accuracy (${(m.find || { a: 0 }).a} charts)`),
    tile(acc(m.name), `Name it accuracy (${(m.name || { a: 0 }).a} charts)`),
    tile(acc(m.work), `Will it work? (${(m.work || { a: 0 }).a} calls)`)));
  const tb = h('tbody');
  for (const k of PRACTICE_KINDS) {
    const s = SAVE.kinds[k] || { a: 0, c: 0 }, lv = level(k), a = s.a ? s.c / s.a : 0;
    tb.append(h('tr', {}, h('td', {}, PAT[k].name), h('td', { class: 'num' }, s.a),
      h('td', {}, h('div', { class: 'row', style: 'flex-wrap:nowrap' }, h('div', { class: 'meter' }, h('i', { style: `width:${Math.round(a * 100)}%` })), h('span', { class: 'num' }, s.a ? pct(a) : '–'))),
      h('td', { class: 'stars' }, starText(lv.stars) + ' ' + lv.label),
      h('td', {}, h('button', { class: 'btn', style: 'padding:4px 10px;font-size:13px', onclick: () => { prefs.kind = k; persistPrefs(); mode = 'find'; startRound(); show('practice'); } }, 'Practise'))));
  }
  v.append(h('div', { class: 'panel tbl-wrap', style: 'margin-top:16px' }, h('table', {},
    h('thead', {}, h('tr', {}, h('th', {}, 'Pattern'), h('th', { class: 'num' }, 'Tries'), h('th', {}, 'Accuracy'), h('th', {}, 'Level'), h('th', {}, ''))), tb)));
  const rs = h('div', { class: 'row', style: 'margin-top:16px' });
  const ask = () => { rs.innerHTML = ''; rs.append(h('span', { class: 'confirm' }, 'Erase all progress in this browser?',
    h('button', { class: 'btn', onclick: () => { SAVE.kinds = {}; SAVE.modes = {}; persist(); session = { a: 0, c: 0 }; renderProgress(); } }, 'Erase'),
    h('button', { class: 'btn', onclick: () => renderProgress() }, 'Keep'))); };
  rs.append(h('button', { class: 'btn', onclick: ask }, 'Reset progress'));
  if (!tried.length) v.append(h('p', { class: 'muted', style: 'margin-top:12px' }, 'No charts answered yet. Your scores appear here as you practise.'));
  v.append(rs);
}

// ---------- do they work? ----------
function renderWorks() {
  const v = $('#view-works'), A = STATS._all;
  v.innerHTML = '';
  v.append(h('div', { class: 'stack', style: 'margin-bottom:16px' },
    h('div', { class: 'eyebrow' }, `Measured on ${A.n.toLocaleString()} patterns in real XAUUSD data`),
    h('h1', {}, 'Do these patterns actually work on gold?'),
    h('p', {}, 'Every pattern found was traded the textbook way: enter at the breakout close, stop and target from the pattern itself. A $0.40 spread-and-slippage cost was taken off each trade. Each result is compared with random entries in the same direction, with the same stop and target sizes, on the same timeframe.')));
  const tile = (n, l) => h('div', { class: 'panel' }, h('b', {}, n), h('span', { class: 'muted' }, l));
  v.append(h('div', { class: 'big' },
    tile(pct(A.target), 'reached the target before the stop'),
    tile(fmtR(A.avgR), 'average per trade, after costs'),
    tile(fmtR(A.baseR), 'random entries, same stop and target'),
    tile('None', 'of the pattern or candle rules tested earlier in this project beat holding gold')));
  v.append(h('div', { class: 'note', style: 'margin-top:16px' },
    'Websites often quote 75-80% success for flags and similar figures for other patterns, usually without a source. On gold, bull flags reached their textbook target first only ' + pct(STATS.bull_flag.target) + ' of the time. ' +
    'Overall the patterns did a little better than random entries, by about a tenth of the risk per trade. The gap was largest on daily and 1-hour charts and close to zero on 5-minute charts once costs were counted. Small groups such as triple tops have too few cases to judge. Earlier tests in this project found no pattern or candle rule that beat simply holding gold. Treat patterns as a way to read the chart and place stops, not as a money machine. Educational only, not investment advice.'));
  const rows = Object.entries(STATS).filter(([k]) => k !== '_all' && PAT[k]).sort((a, b) => (b[1].avgR - b[1].baseR) - (a[1].avgR - a[1].baseR));
  const tb = h('tbody');
  for (const [k, s] of rows) {
    const d = s.avgR - s.baseR;
    tb.append(h('tr', {}, h('td', {}, PAT[k].name), h('td', { class: 'num' }, s.n), h('td', { class: 'num' }, pct(s.target)), h('td', { class: 'num' }, pct(s.stop)),
      h('td', { class: 'num' }, s.rr.toFixed(1) + '×'),
      h('td', { class: 'num ' + (s.avgR >= 0 ? 'pos' : 'neg') }, fmtR(s.avgR)), h('td', { class: 'num' }, fmtR(s.baseR)),
      h('td', { class: 'num ' + (d >= 0 ? 'pos' : 'neg') }, fmtR(d)), h('td', { class: 'muted' }, s.n < 30 ? 'too few to judge' : '')));
  }
  v.append(h('div', { class: 'panel tbl-wrap', style: 'margin-top:16px' }, h('table', {},
    h('thead', {}, h('tr', {}, h('th', {}, 'Pattern'), h('th', { class: 'num' }, 'Found'), h('th', { class: 'num' }, 'Target first'), h('th', { class: 'num' }, 'Stop first'),
      h('th', { class: 'num' }, 'Target / risk'), h('th', { class: 'num' }, 'Avg result'), h('th', { class: 'num' }, 'Random entry'), h('th', { class: 'num' }, 'Difference'), h('th', {}, ''))), tb)));
  v.append(h('p', { class: 'muted', style: 'margin-top:12px;font-size:13px' },
    'R means the amount risked on a trade. Patterns with far targets (pennants, flags) win rarely, so a handful of big winners moves their average a lot. Rows that are neither "target first" nor "stop first" ran out of time (three times the pattern\'s length). Data: MT5 XAUUSD export, daily from 2004, 4-hour from 2013, 1-hour from 2016, 15-minute from 2022, 5-minute from 2025, to 9 Oct 2026. Patterns were found by fixed rules written before looking at results; nothing was tuned on the outcomes.'));
}

// ---------- boot ----------
renderLearn(); renderWorks();
const start = (location.hash || '').slice(1);
show(VIEWS.includes(start) ? start : 'learn');
window.addEventListener('hashchange', () => { const t = location.hash.slice(1); if (VIEWS.includes(t)) show(t); });
