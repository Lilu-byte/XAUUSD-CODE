import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
import ea_replica_v130 as V
from mlib import Harness, SPLIT
R = V.R
H = Harness(); tr = R.h1_trend(H.m1); m = H.m1
T, S = V.run(H, tr, V.D)
o, c = H.o, H.c; spr = H._spr['base']
h = T.module.map(V.D['hold']).values; ei = T.ei.values
x = T.dir.values * (c[ei + h] - o[ei + 1]) - np.where(T.dir.values == 1, spr[ei + 1], spr[ei + h])
T = T.assign(tx=x)
for per, sel in (('train', T.entry < SPLIT), ('test', T.entry >= SPLIT)):
    g = T[sel]
    print(per, 'quantiles', g.tx.quantile([.05, .25, .5, .75, .95]).round(2).to_dict(), 'share > 0', round((g.tx > 0).mean(), 3))
    d = g.groupby(g.entry.dt.normalize()).tx.sum().sort_values()
    print('   worst days', d.head(3).round(1).to_dict()); print('   best days', d.tail(3).round(1).to_dict())
    print('   per-day median', round(d.median(), 2), 'share of days > 0', round((d > 0).mean(), 2), 'n days with trades', len(d))
    # first-minute move only (bracket horizon): dir*(c[ei+1]-o[ei+1]) - spread
    f = g.dir.values * (c[g.ei.values + 1] - o[g.ei.values + 1]) - spr[g.ei.values + 1]
    print('   first-minute close-out (no TP/SL, exit at the entry bar close): mean', round(f.mean(), 3), 'median', round(np.median(f), 3))
print('M1 range in session, test median', round((m.high - m.low)[(m.index >= SPLIT) & (m.tod >= 900) & (m.tod < 1140)].median(), 2),
      ' train', round((m.high - m.low)[(m.index < SPLIT) & (m.tod >= 900) & (m.tod < 1140)].median(), 2))
