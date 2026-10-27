import itertools, pandas as pd, numpy as np
from engine import prep, sim, summ
P = prep('M15')
SPLIT = '2024-07-01'
rows = []
for sig, trig, start, tp, sl, mx, rec in itertools.product(
        list(P['sigs']), ['any', 'pullback'], [75, 600, 930, 990], [3, 5, 8], [3, 5, 8, 12, 20, 30, 50],
        [1, 2, 3], [0, 1]):
    if mx == 1 and rec: continue
    r = sim(P, sig, trig, start, tp, sl, max_tr=mx, recover=rec)
    a, b = r[r.index < SPLIT], r[r.index >= SPLIT]
    sa, sb = summ(a), summ(b)
    rows.append(dict(sig=sig, trig=trig, start=start, tp=tp, sl=sl, max_tr=mx, recover=rec,
                     **{'tr_' + k: v for k, v in sa.items()}, **{'te_' + k: v for k, v in sb.items()}))
g = pd.DataFrame(rows); g.to_csv('/mnt/project-files/xauusd-5-a-day/grid_M15.csv', index=False)
print(len(g), 'combos; train>0:', (g.tr_per_day > 0).mean().round(3), 'test>0:', (g.te_per_day > 0).mean().round(3))
print('corr train/test $/day', g[['tr_per_day', 'te_per_day']].corr().iloc[0, 1].round(3))
cols = ['sig', 'trig', 'start', 'tp', 'sl', 'max_tr', 'recover', 'tr_per_day', 'tr_hit5', 'tr_max_dd', 'te_per_day', 'te_hit5', 'te_max_dd', 'te_pos_months']
print(g.sort_values('tr_per_day', ascending=False)[cols].head(25).round(2).to_string())
print(g.groupby('sig')[['tr_per_day', 'te_per_day']].mean().round(2))
