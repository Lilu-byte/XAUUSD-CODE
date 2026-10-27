"""Hand-crafted bar tests of mlib._sim: costs, fills, gaps, timing, timeouts, slots, halts."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
import mlib


def mk(bars, start='2026-07-01 10:00', spread_pts=20):
    """bars: list of (o,h,l,c) or (o,h,l,c,spread_pts); index minute by minute."""
    idx = pd.date_range(start, periods=len(bars), freq='1min')
    rows = []
    for b in bars:
        sp = b[4] if len(b) > 4 else spread_pts
        rows.append(dict(open=b[0], high=b[1], low=b[2], close=b[3], tick_volume=1.0, spread=float(sp)))
    d = pd.DataFrame(rows, index=idx)
    d['spread_usd'] = d.spread * 0.01
    d['tod'] = d.index.hour * 60 + d.index.minute
    return d


def run(bars, sig, tp, sl, **kw):
    m = mk(bars, **{k: kw.pop(k) for k in list(kw) if k in ('start', 'spread_pts')})
    H = mlib.Harness(m)
    days, tr = H.run(np.array(sig), tp, sl, spread=kw.pop('spread', 'bar'), **kw)
    return days, tr


def show(name, tr, expect=None):
    s = ', '.join(f"(dir={r.dir}, pnl={r.pnl:+.4f}, bars={r.bars})" for r in tr.itertuples())
    ok = ''
    if expect is not None:
        got = list(np.round(tr.pnl.values, 6))
        ok = 'OK' if np.allclose(got, expect, atol=1e-9) else f'MISMATCH expected {expect}'
    print(f'{name:55s} {s}  {ok}')


F = 100.0
flat = (F, F, F, F)
# spread 20 pts = $0.20 ('bar' model)
print('--- cost accounting: flat price, timeout exit ---')
_, tr = run([flat] * 5, [1, 0, 0, 0, 0], 1, 1, timeout=2); show('long flat, timeout 2', tr, [-0.20])
_, tr = run([flat] * 5, [-1, 0, 0, 0, 0], 1, 1, timeout=2); show('short flat, timeout 2', tr, [-0.20])
# spread differs at entry vs exit bar: long pays entry bar spread, short pays exit bar spread
bars = [(F, F, F, F, 10), (F, F, F, F, 50), (F, F, F, F, 30)]
_, tr = run(bars, [1, 0, 0], 1, 1, timeout=2); show('long, entry spr .10, exit spr .30', tr, [-0.10])
_, tr = run(bars, [-1, 0, 0], 1, 1, timeout=2); show('short, entry spr .10, exit spr .30', tr, [-0.30])
_, tr = run(bars, [1, 0, 0], 1, 1, timeout=2, spread='base'); show('long base (+.05)', tr, [-0.15])
_, tr = run(bars, [-1, 0, 0], 1, 1, timeout=2, spread='base'); show('short base (+.05)', tr, [-0.35])
_, tr = run(bars, [1, 0, 0], 1, 1, timeout=2, spread='wide'); show('long wide', tr, [-0.30])

print('--- TP / SL levels (bid for long exits, ask for short) ---')
# long entry ask = 100.20; TP 0.5 => bid must reach 100.70
b = [flat, (F, 100.70, F, 100.6), flat]
_, tr = run(b, [1, 0, 0], 0.5, 0.5, timeout=5); show('long TP: bid high = e+tp exactly', tr, [0.5])
b = [flat, (F, 100.69, F, 100.6), flat]
_, tr = run(b, [1, 0, 0], 0.5, 0.5, timeout=1); show('long: bid high 1c short of TP -> timeout', tr, [100.6 - 100.2])
# short entry bid = 100; TP 0.5 => ask must reach 99.5 => bid low 99.30
b = [flat, (F, F, 99.30, 99.4), flat]
_, tr = run(b, [-1, 0, 0], 0.5, 0.5, timeout=5); show('short TP: bid low 99.30 (ask 99.50)', tr, [0.5])
b = [flat, (F, F, 99.31, 99.4), flat]
_, tr = run(b, [-1, 0, 0], 0.5, 0.5, timeout=1); show('short: bid low 99.31 -> no TP, timeout', tr, [100 - 99.6])
# short SL: ask >= 100.5 => bid high >= 100.3
b = [flat, (F, 100.30, F, F), flat]
_, tr = run(b, [-1, 0, 0], 0.5, 0.5, timeout=5); show('short SL: bid high 100.30', tr, [-0.5])
# long SL: bid <= 99.70
b = [flat, (F, F, 99.70, F), flat]
_, tr = run(b, [1, 0, 0], 0.5, 0.5, timeout=5); show('long SL: bid low 99.70', tr, [-0.5])

print('--- both levels in one bar, fill models ---')
# long: e=100.20, TP=100.70, SL=99.70, open = 100 => q = (100-99.7)/(1.0) = 0.3
for c_, nm in ((100.5, 'bullish'), (99.9, 'bearish')):
    b = [flat, (F, 101, 99, c_), flat]
    for fm in ('STOP', 'FAIR', 'OHLC', 'TARGET'):
        _, tr = run(b, [1, 0, 0], 0.5, 0.5, timeout=5, fill=fm)
        exp = {'STOP': -0.5, 'TARGET': 0.5, 'FAIR': 0.3 * 0.5 + 0.7 * -0.5,
               'OHLC': (-0.5 if c_ > F else 0.5)}[fm]
        show(f'long both-hit {nm} {fm}', tr, [exp])
# short: e=100, ask open = 100.20, TP ask=99.5, SL ask=100.5 => q(TP) = (100.5-100.2)/1.0 = 0.3
for c_, nm in ((100.5, 'bullish'), (99.9, 'bearish')):
    b = [flat, (F, 101, 99, c_), flat]
    for fm in ('STOP', 'FAIR', 'OHLC', 'TARGET'):
        _, tr = run(b, [-1, 0, 0], 0.5, 0.5, timeout=5, fill=fm)
        exp = {'STOP': -0.5, 'TARGET': 0.5, 'FAIR': 0.3 * 0.5 + 0.7 * -0.5,
               'OHLC': (0.5 if c_ > F else -0.5)}[fm]
        show(f'short both-hit {nm} {fm}', tr, [exp])

print('--- gaps: bar opens beyond a level ---')
b = [flat, (99.0, 99.5, 98.8, 99.2), flat]
_, tr = run(b, [1, 0, 0], 0.5, 0.5, timeout=5); show('long gap below SL -> exit at open 99.0', tr, [99.0 - 100.2])
b = [flat, (101.0, 101.5, 100.8, 101.2), flat]
_, tr = run(b, [1, 0, 0], 0.5, 0.5, timeout=5); show('long gap above TP -> exit at open 101 (better)', tr, [101 - 100.2])
b = [flat, (100.5, 100.6, 100.4, 100.5), flat]
_, tr = run(b, [-1, 0, 0], 0.5, 0.5, timeout=5); show('short gap: ask open 100.7 >= SL 100.5', tr, [100 - 100.7])

print('--- timing ---')
# entry bar itself has a huge range after... entry is at close, so entry bar never used for exits
b = [(F, 105, 95, F), flat, flat]
_, tr = run(b, [1, 0, 0], 0.5, 0.5, timeout=1); show('entry bar range ignored (exit on later bars)', tr, [-0.2])
# signal on last bar ignored
_, tr = run([flat] * 3, [0, 0, 1], 0.5, 0.5, timeout=1); print('signal on last bar -> trades:', len(tr))
# timeout counted in bars: timeout=3 -> exits at close of bar i+3
b = [flat, flat, flat, (F, F, F, 100.4), (F, F, F, 100.45)]
_, tr = run(b, [1, 0, 0, 0, 0], 1, 1, timeout=3); show('timeout=3 closes at close of bar i+3', tr, [0.2])
_, tr = run(b, [1, 0, 0, 0, 0], 1, 1, timeout=0); show('timeout=0 closes at close of bar i+1', tr, [-0.2])

print('--- max_open, slot reuse, cooldown ---')
sig = [1, 1, 1, 1, 0, 0, 0, 0]
_, tr = run([flat] * 8, sig, 1, 1, timeout=2, max_open=1); print('max_open=1, timeout=2, 4 consecutive signals ->', list(tr.entry.dt.minute), list(tr.bars))
_, tr = run([flat] * 8, sig, 1, 1, timeout=2, max_open=2); print('max_open=2                              ->', list(tr.entry.dt.minute), list(tr.bars))
_, tr = run([flat] * 8, [1] * 8, 1, 1, timeout=0, max_open=1); print('timeout=0 every bar max_open=1 (slot freed same bar) ->', list(tr.entry.dt.minute))
_, tr = run([flat] * 8, [1] * 8, 1, 1, timeout=0, max_open=1, cooldown=1); print('cooldown=1 ->', list(tr.entry.dt.minute))
_, tr = run([flat] * 8, [1] * 8, 1, 1, timeout=0, max_open=1, cooldown=3); print('cooldown=3 ->', list(tr.entry.dt.minute))

print('--- day target / day loss ---')
# each trade: long, next bar high hits TP 0.3 => +0.3
up = [flat, (F, 100.5, F, F)] * 6
sig = [1, 0] * 6
d, tr = run(up, sig, 0.3, 0.3, timeout=1); print('no target: trades', len(tr), 'day pnl', d.pnl.round(3).tolist())
d, tr = run(up, sig, 0.3, 0.3, timeout=1, day_target=0.8); print('day_target .8: trades', len(tr), 'day pnl', d.pnl.round(3).tolist())
dn = [flat, (F, F, 99.5, F)] * 6
d, tr = run(dn, sig, 0.3, 0.3, timeout=1, day_loss=0.6); print('day_loss .6: trades', len(tr), 'day pnl', d.pnl.round(3).tolist())

print('--- signal values other than +-1 ---')
_, tr = run([flat, (F, 100.7, F, F), flat], [2, 0, 0], 0.5, 0.5, timeout=5); print('sig=+2 traded as dir', tr.dir.tolist(), 'pnl', tr.pnl.round(3).tolist())
_, tr = run([flat, (F, 100.7, F, F), flat], [0.9, 0, 0], 0.5, 0.5, timeout=5); print('sig=0.9 -> trades', len(tr))
