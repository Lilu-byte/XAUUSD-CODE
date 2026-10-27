"""Bridge between P1 (M1) and the M5/M15 ports, on the M1 data only (diagnostics, nothing is selected here):
where does P1's edge live in time, and why can a 5-minute bar not see it?
  - P1 by calendar month and by week; fill-free move after entry by month
  - P1 with the threshold in ATR units (|r3| > 3.4 x ATR240) instead of $7
  - P1 with signals only on M1 bars that close an M5 bar (what an M5-bar EA could see)
  - P1 holding 5 bars (one M5 bar) instead of 3
  - latency 0..4 bars (signal acted on k bars late)"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history')
from vlib import *

m = load_m1(); A = Arr(m)
s = p1_signal(m)
d, t = run(A, s)
P = (('TRAIN', None, SPLIT), ('TEST', SPLIT, None))


def both(name, d, t):
    a = summ(d, t, None, SPLIT); b = summ(d, t, SPLIT, None)
    print(f'{name:52s} TRAIN {a["per_day"]:+6.2f}/day {a["trades_day"]:5.1f} tr/d {a["per_trade"]:+.3f}/tr | '
          f'TEST {b["per_day"]:+6.2f}/day {b["trades_day"]:5.1f} tr/d {b["per_trade"]:+.3f}/tr')


both('P1 as specified', d, t)
mon = d.pnl.groupby(d.index.to_period('M')).agg(['mean', 'size'])
tm = t.groupby(t.entry.dt.to_period('M')).pnl.agg(['mean', 'size'])
print('P1 by month ($/day, days, $/trade, trades): ' + '; '.join(f'{k}: {r["mean"]:+.2f} ({int(r["size"])}d, {tm.loc[k, "mean"]:+.3f}/tr, {int(tm.loc[k, "size"])}t)' for k, r in mon.iterrows()))
# fill-free move after the next-bar-open entry, by month
sf = ea_filter(m, s)
for k in (1, 3):
    mv = ((m.close.shift(-k) - m.open.shift(-1)) * sf)[sf != 0]
    print(f'fill-free move {k}m after entry (no spread) by month: ' + ', '.join(f'{p}: {v:+.3f}' for p, v in mv.groupby(mv.index.to_period('M')).mean().items()))
atr = (m.high - m.low).rolling(240).mean().values
r3 = (m.close - m.close.shift(3)).values
sn = np.where(np.abs(r3) > 3.4 * atr, -np.sign(r3), 0.0)
both('P1 with threshold 3.4 x ATR240 instead of $7', *run(A, sn))
on5 = (m.index.minute % 5) == 4
both('P1 only on M1 bars that close an M5 bar', *run(A, np.where(on5, s, 0)))
both('P1 NOT on M5-closing bars (complement)', *run(A, np.where(~on5, s, 0)))
both('P1 holding 5 bars', *run(A, s, timeout=5))
both('P1 holding 5 bars, only M5-closing bars', *run(A, np.where(on5, s, 0), timeout=5))
r5 = (m.close - m.close.shift(5)).values
k5 = np.nanquantile(np.abs(r5)[(m.tod.values >= 65)], 1 - 0.0216)
s5 = np.where(np.abs(r5) > k5, -np.sign(r5), 0.0)
both(f'5-minute move > ${k5:.2f} (same rate), M5-closing bars, hold 5', *run(A, np.where(on5, s5, 0), timeout=5))
for L in range(5):
    both(f'P1 latency {L} bar(s)', *run(A, s, latency=L))
# where inside the 3 holding minutes does the P1 money come from? per-trade gross move bar by bar after entry
sel = np.flatnonzero(sf != 0); sel = sel[sel + 4 < len(m)]
o1 = m.open.values[sel + 1]
for per, msk in (('TRAIN', m.index[sel] < SPLIT), ('TEST', m.index[sel] >= SPLIT)):
    seg = []
    prev = o1
    for j in (1, 2, 3):
        cj = m.close.values[sel + j]
        seg.append(((cj - prev) * sf[sel])[msk].mean()); prev = cj
    gap = ((m.open.values[sel + 1] - m.close.values[sel]) * sf[sel])[msk].mean()
    print(f'{per}: fade-direction move, signal close -> next open {gap:+.3f}; then bar1 {seg[0]:+.3f}, bar2 {seg[1]:+.3f}, bar3 {seg[2]:+.3f} (per signal, no spread)')
