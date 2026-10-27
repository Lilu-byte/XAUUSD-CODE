import sys, numpy as np; sys.path.insert(0, '.')
from engine import prep, sim, summ, load
from patterns import detect
for tf, split, lo in (('M15', '2024-07-01', '2022-07-08'), ('M5', '2026-01-01', '2025-05-06')):
    P = prep(tf); d = load(tf); d = d[d.index.dayofweek < 5]; pats = detect(d)
    a = pats['Any pattern (net vote)'].values
    P['sigs']['any+H1'] = np.where(a == P['sigs']['H1'], a, 0)
    for ml in (1e9, 20, 10):
        for fair in (1, 0):
            r = sim(P, 'any+H1', 'any', 75, 5, 12, target=5, max_tr=50, maxloss=ml, fair=fair); r = r[r.index >= lo]
            print(tf, 'daily loss limit', ml, 'fair fills' if fair else 'stop-first fills',
                  {k: round(float(v), 2) for k, v in summ(r[r.index >= split]).items() if k in ('per_day', 'hit5', 'loss_days', 'worst_month', 'max_dd', 'pos_months', 'trades_day')})
