# Edge cases of Redraw()'s maths, run on the literal port (frvp_port.py) and checked against the
# exact-integer reference (frvp_ref.py) where that makes sense.
import sys, math, random
import numpy as np
import pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-volume-profile/review/maths')
from frvp_port import redraw, RowOf
import frvp_ref as ref
from common import load


def P(c, **kw):
    return redraw([x[1] for x in c], [x[2] for x in c], [x[0] for x in c], [x[3] for x in c], [x[4] for x in c], **kw)


def R(c, **kw):
    df = pd.DataFrame(c, columns=['open', 'high', 'low', 'close', 'tick_volume'])
    return ref.profile(df, **kw)


def show(tag, p):
    if p is None:
        print(f"  {tag}: no profile (sum <= 0)"); return
    nz = [k for k in range(p['rows']) if p['tot'][k] > 0]
    print(f"  {tag}: rows {p['rows']} base {p['base']:.6f} step {p['step']:.6g} | non-zero rows {nz[:6]}{'...' if len(nz) > 6 else ''} "
          f"| POC row {p['poc']} px {p['pocPx']:.5f} | VA rows {p['vaLo']}..{p['vaHi']} VAL {p['val']:.5f} VAH {p['vah']:.5f} "
          f"| share {p['acc']/p['sum']*100:.2f}%")


print("1) hi == lo (every candle at one price)")
c = [(4030.37, 4030.37, 4030.37, 4030.37, 120)]
show("one candle h==l, rows=60   ", P(c, InpRows=60))
show("one candle h==l, size=0.50 ", P(c, InpRowSize=0.5))
c2 = [(4030.00, 4030.00, 4030.00, 4030.00, 50), (4030.00, 4030.00, 4030.00, 4030.00, 70)]
show("two candles at 4030.00, size=1.00", P(c2, InpRowSize=1.0))
show("two candles at 4030.00, rows=24  ", P(c2, InpRows=24))

print("\n2) candles with high == low inside a wider range (point masses)")
c = [(4000.00, 4010.00, 4000.00, 4010.00, 100), (4005.00, 4005.00, 4005.00, 4005.00, 40),
     (4002.50, 4002.50, 4002.50, 4002.50, 30)]
for kw in (dict(InpRows=20), dict(InpRowSize=0.5), dict(InpRowSize=1.0)):
    p = P(c, **kw); r = R(c, rows=kw.get('InpRows', 60), rowsize=kw.get('InpRowSize', 0.0))
    k5 = RowOf(4005.0, p['base'], p['step'], p['rows']); k25 = RowOf(4002.5, p['base'], p['step'], p['rows'])
    print(f"  {kw}: 4005.00 point mass -> row {k5} (rl {p['base']+k5*p['step']:.4f}), 4002.50 -> row {k25} "
          f"(rl {p['base']+k25*p['step']:.4f}); max|port-ref| {np.max(np.abs(np.array(p['tot'])-r['tot'])):.2e}")
# exhaustive: cent prices that fall exactly on a row bound in row-count mode, floating RowOf vs exact
random.seed(7)
mis = tot = 0; ex = []
for _ in range(3000):
    lo = round(random.uniform(1200, 5000), 2)
    rows = random.choice([24, 30, 40, 50, 60, 100, 120, 200])
    W = random.choice([rows * m for m in (1, 2, 5, 10, 25, 50, 100)])   # range in cents so bounds fall on cents
    hi = round(lo + W / 100, 2)
    base, step = lo, (hi - lo) / rows
    for k in range(1, rows):
        pc = int(round(lo * 100)) + k * W // rows
        p = pc / 100.0
        got = RowOf(p, base, step, rows); tot += 1
        if got != k:
            mis += 1
            if len(ex) < 3: ex.append((lo, hi, rows, k, p, got))
print(f"  row-count mode: a price exactly on a row bound goes to the row ABOVE (k) by the code's rule; "
      f"floating RowOf put it in another row in {mis} of {tot} cases ({mis/tot*100:.2f}%), e.g. {ex}")

print("\n3) candle whose high is exactly on a row boundary")
c = [(4000.00, 4001.00, 4000.00, 4001.00, 100)]      # rows of 0.50: 4000-4000.5, 4000.5-4001; high is on the bound of row 2
pc = [(3999.00, 4003.00, 3999.00, 4003.00, 1)] + c    # wider range so the bound is interior
p = P(pc, InpRowSize=0.5); r = R(pc, rowsize=0.5)
print(f"  size=0.50: base {p['base']} rows {p['rows']}; row 4 (4001.00-4001.50) port {p['tot'][4]!r} ref {r['tot'][4]!r}; "
      f"rows 2,3 port {p['tot'][2]:.6f},{p['tot'][3]:.6f}")
lv = R(pc, rowsize=0.5, model='levels')
print(f"  same candle under the discrete price-level model: row 4 gets {lv['tot'][4]:.4f} (1 of 101 cent levels of 100 ticks + the 1-tick candle)")
# row-count mode: high on a floating bound -> tiny spurious volume in the row above?
random.seed(3)
spur = 0; maxsp = 0.0; trials = 0
for _ in range(3000):
    lo = round(random.uniform(1200, 5000), 2); rows = 60; W = rows * random.choice([1, 2, 5, 10, 50])
    hi = round(lo + W / 100, 2); k = random.randint(1, rows - 2)
    bnd = round((int(round(lo * 100)) + k * W // rows) / 100, 2)
    l = round(bnd - random.choice([0.01, 0.05, 0.37]), 2)
    if l < lo: continue
    cs = [(lo, lo + 0.01, lo, lo + 0.01, 1), (hi - 0.01, hi, hi - 0.01, hi, 1), (l, bnd, l, bnd, 1000)]
    p = P(cs, InpRows=rows); trials += 1
    extra = p['tot'][k] - (1 if k == 0 else 0)
    if extra > 0: spur += 1; maxsp = max(maxsp, extra / 1000)
print(f"  row-count mode, high on a bound: the row above got a non-zero share in {spur} of {trials} cases, max share {maxsp:.2e}")

print("\n4) top row (price == hi)")
c = [(4000.00, 4010.00, 4000.00, 4010.00, 100), (4010.00, 4010.00, 4010.00, 4010.00, 50)]
for kw in (dict(InpRowSize=0.5), dict(InpRowSize=1.0), dict(InpRows=20)):
    p = P(c, **kw); r = R(c, rows=kw.get('InpRows', 60), rowsize=kw.get('InpRowSize', 0.0))
    print(f"  {kw}: rows {p['rows']} top bound {p['base']+p['rows']*p['step']:.2f}; point mass at hi -> row "
          f"{RowOf(4010.0, p['base'], p['step'], p['rows'])} (top row {p['rows']-1}); top row port {p['tot'][-1]:.4f} ref {r['tot'][-1]:.4f}")

print("\n5) row-size alignment: base = MathFloor(lo/step)*step versus the exact multiple of step at or below lo")
for step in (0.05, 0.10, 0.20, 0.25, 0.50, 1.00, 2.50, 5.00, 10.0):
    sc = int(round(step * 100)); low_extra = above = 0; n = 0
    for c in range(100000, 500001, 1):              # every cent price from 1000.00 to 5000.00
        lo = c / 100.0
        base = math.floor(lo / step) * step
        exact = (c // sc) * sc / 100.0
        n += 1
        if base < exact - 1e-9: low_extra += 1      # one step too low: an extra empty bottom row
        elif base > lo: above += 1                  # base a hair above lo (row 0 clamp absorbs it)
    print(f"  step {step:5.2f}: base one step too low in {low_extra} of {n} prices; base above lo (by rounding) in {above}")

print("\n6) rows capped at 2000")
d = load('M5'); m = d.loc['2026-01-01':'2026-01-31 23:59']
for rs in (0.5, 0.65, 1.0):
    p = redraw(m['high'].tolist(), m['low'].tolist(), m['open'].tolist(), m['close'].tolist(), m['tick_volume'].tolist(), InpRowSize=rs)
    print(f"  M5 Jan 2026 (lo {p['lo']:.2f} hi {p['hi']:.2f}) size={rs}: rows {p['rows']} step {p['step']:.6f} base {p['base']:.2f} "
          f"capped {p['capped']} -> POC {p['pocPx']:.4f} VAL {p['val']:.4f} VAH {p['vah']:.4f}")
for rs in (1e-6, 1e-7):
    nr = math.ceil((4600.00 - math.floor(4300.00 / rs) * rs) / rs - 1e-9)
    print(f"  row size {rs:g} on a $300 range: MathCeil(...) = {nr:.4g} rows {'> INT_MAX: the (int) cast on line 294 is out of range before the 2000 cap is tested' if nr > 2**31 - 1 else '(fits in int, capped to 2000)'}")

print("\n7) range of 1 candle (source TF == chart TF), 60 rows")
random.seed(11)
pocs = []; vas = []; spreads = []
for _ in range(2000):
    lo = round(random.uniform(1800, 4200), 2); hi = round(lo + random.uniform(0.3, 15), 2)
    p = P([(lo, hi, lo, hi, random.randint(20, 3000))], InpRows=60)
    t = p['tot']; spreads.append((max(t) - min(t)) / max(t))
    pocs.append(p['poc']); vas.append((p['vaLo'], p['vaHi']))
pocs = np.array(pocs)
print(f"  POC row 29 (nearest the middle under the tie rule): {np.mean(pocs == 29)*100:.1f}%; |POC-29.5| > 5 rows: {np.mean(np.abs(pocs-29.5) > 5)*100:.1f}%")
print(f"  relative spread between rows that should be equal: median {np.median(spreads):.2e}, max {max(spreads):.2e} (POC tie tolerance is 1e-12)")
cent = [(lo + hi) / 2 - 29.5 for lo, hi in vas]
print(f"  value area: 42 rows every time? {all(hi - lo + 1 == 42 for lo, hi in vas)}; centre of VA minus centre of grid, rows: "
      f"min {min(cent):+.1f} max {max(cent):+.1f}; centred within 1 row: {np.mean(np.abs(np.array(cent)) <= 1)*100:.1f}%")
# the same single candle with the overlaps computed in row units (proposed fix), and the VA tie (above >= below)
def fixed(lo, hi, v, rows=60, tie_up=True):
    base, step = lo, (hi - lo) / rows
    pl, ph = (lo - base) / step, (hi - base) / step
    tot = [0.0] * rows
    a, b = RowOf(lo, base, step, rows), RowOf(hi, base, step, rows)
    for k in range(a, b + 1):
        rl, rh = float(k), float(k + 1)
        if k == rows - 1: rh = max(rh, ph)
        if k == 0: rl = min(rl, pl)
        ov = min(ph, rh) - max(pl, rl)
        if ov > 0: tot[k] += v * ov / (ph - pl)
    return tot
random.seed(11); fp = []; fs = []
for _ in range(2000):
    lo = round(random.uniform(1800, 4200), 2); hi = round(lo + random.uniform(0.3, 15), 2)
    t = fixed(lo, hi, random.randint(20, 3000)); fs.append((max(t) - min(t)) / max(t))
    maxv = 0; poc = 0; mid = 29.5
    for k in range(60):
        if t[k] > maxv * (1 + 1e-12) or (t[k] >= maxv * (1 - 1e-12) and t[k] > 0 and abs(k - mid) < abs(poc - mid)): maxv = t[k]; poc = k
    fp.append(poc)
print(f"  overlaps in row units ((p-base)/step) instead of prices: max relative spread {max(fs):.2e}; POC row 29: {np.mean(np.array(fp) == 29)*100:.1f}%")

print("\n8) up/down split: a candle with close == open counts as up (line 312)")
for tf in ('M1', 'M5', 'H1'):
    d = load(tf); dj = d['close'] == d['open']
    print(f"  {tf}: doji candles {dj.sum()} of {len(d)}, {d.loc[dj,'tick_volume'].sum()/d['tick_volume'].sum()*100:.2f}% of tick volume")
