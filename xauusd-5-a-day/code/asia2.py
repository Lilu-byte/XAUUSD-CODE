import numpy as np, pandas as pd
from engine import prep, sim, summ
f = lambda d: {k: round(float(v), 2) for k, v in d.items()}
for tf, lo, hi in (('H1', '2016-08-01', '2022-07-01'), ('M15', '2022-07-08', '2026-10-10'), ('M5', '2025-05-06', '2026-10-10')):
    P = prep(tf)
    if tf == 'M5': P['sc'] = np.ones_like(P['sc'])   # M5 row = the EA's fixed-dollar rule
    s = P['sigs']['asia_break']
    P['sigs']['ab_long'] = np.clip(s, 0, None); P['sigs']['ab_short'] = np.clip(s, None, 0)
    nz = s != 0
    for tp, sl in ((5, 30), (5, 50), (8, 50)):
        for sig in ('asia_break', 'ab_long', 'ab_short'):
            r = sim(P, sig, 'any', 540, tp, sl); r = r[(r.index >= lo) & (r.index < hi)]
            yr = r.pnl.groupby(r.index.year).mean().round(2).to_dict()
            print(tf, tp, sl, sig, f(summ(r)), 'by year $/day', yr)
        nulls = []
        for seed in range(100):
            flip = np.where(np.random.default_rng(seed).random(P['day'][-1] + 1) < .5, 1., -1.)[P['day']]
            P['sigs']['null'] = np.where(nz, flip, 0)
            r = sim(P, 'null', 'any', 540, tp, sl); r = r[(r.index >= lo) & (r.index < hi)]; nulls.append(r.pnl.mean())
        print('   null random direction: median', round(np.median(nulls), 2), '95th', round(np.percentile(nulls, 95), 2))
