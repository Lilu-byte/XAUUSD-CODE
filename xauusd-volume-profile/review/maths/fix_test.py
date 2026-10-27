# Tests the three proposed changes on a copy of the port (the .mq5 is not touched):
#  A) overlaps in row units (lines 316-323), B) value-area tie goes to the shorter side (line 353),
#  C) row-size cap keeps a multiple of the chosen row size (lines 290-297).
import sys, math, random
import numpy as np
sys.path.insert(0, '/mnt/project-files/xauusd-volume-profile/review/maths')
from frvp_port import RowOf
from common import sel
import frvp_ref as ref

def redraw_fixed(H, L, O, C, V, InpRows=60, InpRowSize=0.0, pct=70.0, _Point=0.01):
    hi, lo = max(H), min(L)
    if hi - lo < _Point: hi = lo + _Point
    if InpRowSize > 0:
        step = InpRowSize; base = math.floor(lo / step) * step
        nr = math.ceil((hi - base) / step - 1e-9)                 # stays a double: no int overflow
        if nr > 2000:
            m = math.ceil(nr / 2000.0)
            while True:
                step = InpRowSize * m; base = math.floor(lo / step) * step
                nr = math.ceil((hi - base) / step - 1e-9)
                if nr <= 2000: break
                m += 1
        rows = max(1, int(nr))
    else:
        rows = InpRows; base = lo; step = (hi - lo) / rows
    up = [0.0] * rows; dn = [0.0] * rows
    for i in range(len(H)):
        v = float(V[i]);
        if v <= 0: continue
        isup = C[i] >= O[i]; h, l = H[i], L[i]; tgt = up if isup else dn
        a, b = RowOf(l, base, step, rows), RowOf(h, base, step, rows)
        if a == b or h - l < _Point * 0.5: tgt[a] += v; continue
        pl, ph = (l - base) / step, (h - base) / step
        for k in range(a, b + 1):
            rl, rh = float(k), float(k + 1)
            if k == rows - 1: rh = max(rh, ph)
            if k == 0: rl = min(rl, pl)
            ov = min(ph, rh) - max(pl, rl)
            if ov > 0: tgt[k] += v * ov / (ph - pl)
    tot = [up[k] + dn[k] for k in range(rows)]
    s = 0.0; maxv = 0.0; mid = (rows - 1) / 2.0; poc = 0
    for k in range(rows):
        s += tot[k]
        if tot[k] > maxv * (1 + 1e-12) or (tot[k] >= maxv * (1 - 1e-12) and tot[k] > 0 and abs(k - mid) < abs(poc - mid)):
            maxv = tot[k]; poc = k
    target = s * pct / 100.0; acc = tot[poc]; vaLo = vaHi = poc
    while acc < target - s * 1e-12 and (vaLo > 0 or vaHi < rows - 1):
        above = tot[vaHi + 1] if vaHi < rows - 1 else -1.0
        below = tot[vaLo - 1] if vaLo > 0 else -1.0
        goUp = above > below * (1 + 1e-9) or (above >= below * (1 - 1e-9) and vaHi - poc <= poc - vaLo)
        if goUp: vaHi += 1; acc += tot[vaHi]
        else: vaLo -= 1; acc += tot[vaLo]
    return dict(rows=rows, base=base, step=step, tot=tot, poc=poc, vaLo=vaLo, vaHi=vaHi, acc=acc, sum=s,
                pocPx=base + (poc + 0.5) * step, vah=base + (vaHi + 1) * step, val=base + vaLo * step)

random.seed(11); pocs = []; vas = set()
for _ in range(2000):
    lo = round(random.uniform(1800, 4200), 2); hi = round(lo + random.uniform(0.3, 15), 2)
    p = redraw_fixed([hi], [lo], [lo], [hi], [500]); pocs.append(p['poc']); vas.add((p['vaLo'], p['vaHi']))
print(f"single candle, 60 rows, fixed: POC row 29 in {pocs.count(29)} of 2000; value areas seen {sorted(vas)}")

# real ranges: fixed port vs the independent reference (grid the same as the reference when not capped)
worst = 0.0; vadiff = 0; n = 0
for t0, t1 in [('2026-10-02 16:00', '2026-10-02 16:59'), ('2026-10-08 00:00', '2026-10-08 23:59'), ('2026-09-28 00:00', '2026-10-02 23:59'),
               ('2026-09-01 00:00', '2026-09-30 23:59'), ('2026-06-26 00:00', '2026-10-09 23:59')]:
    d = sel('M1', t0, t1)
    for c in (dict(InpRows=24), dict(InpRows=60), dict(InpRows=120), dict(InpRowSize=0.5), dict(InpRowSize=1.0), dict(InpRowSize=5.0)):
        p = redraw_fixed(d['high'].tolist(), d['low'].tolist(), d['open'].tolist(), d['close'].tolist(), d['tick_volume'].tolist(), **c)
        r = ref.profile(d, rows=c.get('InpRows', 60), rowsize=c.get('InpRowSize', 0.0))
        worst = max(worst, float(np.max(np.abs(np.array(p['tot']) - r['tot']))) / float(r['tot'].max()))
        vadiff += int((p['vaLo'], p['vaHi'], p['poc']) != (r['vaLo'], r['vaHi'], r['poc'])); n += 1
print(f"real M1 ranges, fixed port vs reference: {n} profiles, max row diff {worst:.1e} of the POC row, POC/VA rows different in {vadiff}")

for rs, (t0, t1, tf) in ((0.5, ('2026-01-01', '2026-01-31 23:59', 'M5')), (1.0, ('2016-01-01', '2026-12-31', 'H1')), (1e-7, ('2026-09-01', '2026-09-30 23:59', 'M1'))):
    d = sel(tf, t0, t1)
    p = redraw_fixed(d['high'].tolist(), d['low'].tolist(), d['open'].tolist(), d['close'].tolist(), d['tick_volume'].tolist(), InpRowSize=rs)
    print(f"cap, {tf} {t0[:7]}..{t1[:7]} size {rs:g}: rows {p['rows']} step {p['step']:.7g} base {p['base']:.2f} -> POC {p['pocPx']:.2f} VAL {p['val']:.2f} VAH {p['vah']:.2f}")
