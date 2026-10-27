"""Each candlestick pattern as an entry signal: trade its direction at the pattern's close,
take profit / stop in $, keep trading until the day is +$5 (or 23:15), one trade open at a time."""
import sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, '.')
from engine import prep, sim, summ, load
from patterns import detect
out = []
for tf, split, lo in (('M15', '2024-07-01', '2022-07-08'), ('M5', '2026-01-01', '2025-05-06')):
    P = prep(tf)
    d = load(tf); d = d[d.index.dayofweek < 5]
    pats = detect(d)
    for k, v in pats.items():
        P['sigs'][k] = v.values
        P['sigs'][k + ' + H1 trend'] = np.where(v.values == P['sigs']['H1'], v.values, 0)
    names = [k for k in pats] + [k + ' + H1 trend' for k in pats]
    rng = np.random.default_rng(0)
    for name, tp, sl in itertools.product(names, (1, 2, 3, 5), (1, 2, 3, 5, 8, 12, 20)):
        r = sim(P, name, 'any', 75, tp, sl, target=5.0, max_tr=50)
        r = r[r.index >= lo]
        a, b = summ(r[r.index < split]), summ(r[r.index >= split])
        out.append(dict(tf=tf, pattern=name, tp=tp, sl=sl, **{'tr_' + x: a[x] for x in ('per_day', 'hit5', 'trades_day')},
                        **{'te_' + x: b[x] for x in ('per_day', 'hit5', 'trades_day', 'worst_day', 'max_dd', 'pos_months')}))
    # coin-flip baseline: same entry bars as the "any pattern" signal, random direction
    nz = pats['Any pattern (net vote)'].values != 0
    for tp, sl in itertools.product((1, 2, 3, 5), (1, 2, 3, 5, 8, 12, 20)):
        vals = []
        for seed in range(20):
            P['sigs']['null'] = np.where(nz, np.where(np.random.default_rng(seed).random(len(nz)) < .5, 1., -1.), 0)
            r = sim(P, 'null', 'any', 75, tp, sl, max_tr=50); r = r[r.index >= lo]
            vals.append((summ(r[r.index < split])['per_day'], summ(r[r.index >= split])['per_day']))
        v = np.array(vals)
        out.append(dict(tf=tf, pattern='COIN FLIP (same bars)', tp=tp, sl=sl, tr_per_day=v[:, 0].mean(), te_per_day=v[:, 1].mean()))
g = pd.DataFrame(out); g.to_csv('/mnt/project-files/xauusd-candles/grid.csv', index=False)
pd.set_option('display.width', 250)
for tf in ('M15', 'M5'):
    x = g[g.tf == tf]
    print('=====', tf, 'combos', len(x), 'positive train', (x.tr_per_day > 0).mean().round(3), 'positive test', (x.te_per_day > 0).mean().round(3),
          'corr', x[['tr_per_day', 'te_per_day']].corr().iloc[0, 1].round(2))
    best = x.sort_values('tr_per_day', ascending=False).groupby('pattern').head(1).sort_values('tr_per_day', ascending=False)
    print(best[['pattern', 'tp', 'sl', 'tr_per_day', 'tr_trades_day', 'te_per_day', 'te_hit5', 'te_trades_day', 'te_worst_day', 'te_max_dd']].round(2).to_string(index=False))
