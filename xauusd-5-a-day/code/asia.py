import numpy as np, pandas as pd
from engine import prep, sim, summ
P = prep('M15'); SPLIT = '2024-07-01'
def both(sig, **k):
    r = sim(P, sig, 'any', 540, **k); return summ(r[r.index < SPLIT])['per_day'], summ(r[r.index >= SPLIT])['per_day'], summ(r)
print('asia_break neighbourhood (train, test $/day), max_tr=1')
for tp in (3, 5, 8, 12):
    print(tp, [tuple(round(x, 2) for x in both('asia_break', tp=tp, sl=sl)[:2]) for sl in (8, 12, 20, 30, 50, 80)])
# null: same entry times as asia_break, random direction
s = P['sigs']['asia_break'].copy(); nz = s != 0
res = []
for seed in range(200):
    rng = np.random.default_rng(seed)
    flip = np.where(rng.random(P['day'][-1] + 1) < .5, 1., -1.)[P['day']]
    P['sigs']['null'] = np.where(nz, flip, 0)
    a, b, _ = both('null', tp=8, sl=50); res.append((a, b, (a * 518 + b * 581) / 1099))
res = np.array(res); a, b, full = both('asia_break', tp=8, sl=50)
print('real', round(a, 2), round(b, 2), {k: round(v, 2) for k, v in full.items()})
print('null full-period $/day pct: 50%', np.percentile(res[:, 2], 50).round(2), '95%', np.percentile(res[:, 2], 95).round(2),
      'share null >= real full', (res[:, 2] >= full['per_day']).mean())
