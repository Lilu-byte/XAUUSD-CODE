"""(4) look-ahead truncation test; random baseline with the pick's long share; robustness of the random comparison
to the few largest trades."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/repro')
from vlib import *

d = load(M15_FILE, 15, 'month_hour'); dates = pd.DatetimeIndex(np.unique(d.date.values))
s, ar, vw, mv = signal(d); base = d.spr_bar.values + 0.05
el = eligible(d)

# ---- truncation test: recompute signal (and AR, VWAP, move) on data cut right after bar i
rng = np.random.default_rng(11)
sig_bars = np.where(s != 0)[0]
cand = np.r_[rng.integers(40, len(d) - 1, 400), rng.choice(sig_bars, 200, replace=False)]
bad = 0; badf = 0
for i in cand:
    dc = d.iloc[:i + 1].copy()
    dc['step_next'] = False                          # unknown future
    sc, arc, vwc, mvc = signal(dc)
    bad += int(sc[i] != s[i])
    badf += int(not (np.isclose(arc[i], ar[i], equal_nan=True) and np.isclose(vwc[i], vw[i]) and np.isclose(mvc[i], mv[i], equal_nan=True)))
print(f'truncation test: {len(cand)} bars (400 random + 200 signal bars): signal mismatches {bad}, feature mismatches {badf}')

T = trades(d, s, base)
a = stats(T, dates, *TRAIN); b = stats(T, dates, *TEST)
# ---- random directions with the pick's long share per period (drift-matched)
ls = {'TRAIN': a['long_share'], 'TEST': b['long_share']}
res = {}
for nm, per, pk in (('TRAIN', TRAIN, a), ('TEST', TEST, b)):
    out = []
    for z in range(50):
        r = np.where(np.random.default_rng(2000 + z).random(len(s)) < ls[nm], 1, -1)
        Tr = trades(d, np.where(s != 0, r, 0), base)
        out.append(stats(Tr, dates, *per)['per_day'])
    out = np.array(out)
    print(f'{nm}: random with long share {ls[nm]:.2f}: mean {out.mean():+.3f} sd {out.std():.3f}, share >= pick {(out >= pk["per_day"]).mean():.2f}, z {(pk["per_day"] - out.mean()) / out.std():+.2f}')

# ---- random comparison with the largest trades removed (same bars removed for random)
for drop in (1, 3, 5, 10):
    for nm, per in (('TRAIN', TRAIN), ('TEST', TEST)):
        Tp = T[(T.entry >= per[0]) & (T.entry < per[1])]
        keep_i = set(Tp.i) - set(Tp.sort_values('pnl', ascending=False).head(drop).i)
        mask = np.isin(np.arange(len(s)), list(keep_i)) | ((d.index < pd.Timestamp(per[0])) | (d.index >= pd.Timestamp(per[1])))
        s2 = np.where(mask, s, 0)
        pk = stats(trades(d, s2, base), dates, *per)['per_day']
        rr = np.array([stats(trades(d, np.where(s2 != 0, np.where(np.random.default_rng(3000 + z).random(len(s)) < .5, 1, -1), 0), base), dates, *per)['per_day'] for z in range(50)])
        print(f'  drop top {drop:2d} trades of {nm}: pick {pk:+.3f}/d, random mean {rr.mean():+.3f}, share of seeds >= pick {(rr >= pk).mean():.2f}')

# ---- per quarter: pick vs 50-seed random mean (base)
p = per_day(T, dates)
R = np.mean([per_day(trades(d, np.where(s != 0, np.where(np.random.default_rng(1000 + z).random(len(s)) < .5, 1, -1), 0), base), dates).values for z in range(50)], axis=0)
q = pd.DataFrame({'pick': p.values, 'rand': R}, index=dates).groupby(dates.to_period('Q').astype(str)).mean()
q['excess'] = q.pick - q.rand
print('quarters pick-minus-random $/day: ' + ' '.join(f'{k}:{v:+.2f}' for k, v in q.excess.items()))
print(f'quarters with pick > random: {(q.excess > 0).sum()}/{len(q)}; quarters with pick > 0: {(q.pick > 0).sum()}/{len(q)}')
