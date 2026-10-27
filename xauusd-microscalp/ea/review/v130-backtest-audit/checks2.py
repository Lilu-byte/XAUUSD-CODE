import sys, itertools
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
import ea_replica_v130 as V
from mlib import Harness, SPLIT, random_like, spread_series, FILL
from ea_sim import _sim_next
R = V.R
H = Harness(); tr = R.h1_trend(H.m1); m = H.m1
# 1) grid re-run, compare with stored csv
rows = []
for tp, mult, pct, body, m5 in itertools.product((0.15, 0.20, 0.25, 0.30), (2.0, 2.5, 3.0), (40, 50), (0.0, 0.5, 0.8), ('off', 'candle', 'ema')):
    p = dict(V.D, tp=tp, sl=round(tp * mult, 2), spread_pct=pct, body=body, m5=m5)
    T, _ = V.run(H, tr, p)
    a = V.score(T, H.dates, 'train'); b = V.score(T, H.dates, 'test')
    rows.append(dict(tp=tp, sl=p['sl'], pct=pct, body=body, m5=m5, tr=a['per_day'], tr_n=a['trades_day'], te=b['per_day'], te_n=b['trades_day'], te_pt=b['per_trade']))
G = pd.DataFrame(rows)
old = pd.read_csv('/mnt/project-files/xauusd-microscalp/ea/v130_grid.csv')
print('grid rows', len(G), 'stored', len(old))
mg = G.merge(old, on=['tp', 'sl', 'pct', 'body', 'm5'])
print('max |train diff| vs stored', (mg.tr - mg.tr_per_day).abs().max(), ' max |test diff|', (mg.te - mg.te_per_day).abs().max())
print('share >0 train', (G.tr > 0).mean(), 'test', (G.te > 0).mean(), ' share >=0 test', (G.te >= 0).mean())
print('versions with ZERO test trades', (G.te_n == 0).sum(), ' with <1 trade/day test', (G.te_n < 1).sum())
print('best test per day', G.te.max(), ' best train', G.tr.max())
print(G.sort_values('tr', ascending=False).head(8).to_string(index=False))
print('test per_day == 0 rows:'); print(G[G.te == 0].head(10).to_string(index=False))
