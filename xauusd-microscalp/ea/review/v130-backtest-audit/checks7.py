import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
import ea_replica_v130 as V
from mlib import Harness, SPLIT, random_like
R = V.R
H = Harness(); tr = R.h1_trend(H.m1); m = H.m1
# session coverage per day
ins = (m.tod >= 900) & (m.tod < 1140)
cnt = pd.Series(ins.values, index=m.index.normalize()).groupby(level=0).sum()
print('days with < 200 session bars:', cnt[cnt < 200].to_dict())
T, S = V.run(H, tr, V.D, spread='bar', filt='bar')
s_te = R.per_day(T, H.dates)[H.dates >= SPLIT].mean()
rte = []
for z in range(200):
    Sr = {k: random_like(v, 50000 + z * 10 + i).astype(np.int64) for i, (k, v) in enumerate(S.items())}
    Tr, _ = V.run(H, tr, V.D, S=Sr, spread='bar', filt='bar'); rte.append(R.per_day(Tr, H.dates)[H.dates >= SPLIT].mean())
rte = np.array(rte)
print(f'bar/bar: strategy test {s_te:.3f}/day; random 200 median {np.median(rte):.3f}, share random >= strategy {(rte >= s_te).mean():.3f}')
# last 3 test weeks only
T, S = V.run(H, tr, V.D)
late = pd.Timestamp('2026-09-21'); dd = H.dates[H.dates >= late]
g = T[T.entry >= late]
print('defaults, Sep 21-Oct 9:', len(dd), 'days, trades/day', round(len(g) / len(dd), 2), 'per trade', round(g.pnl.mean(), 3), 'per day', round(g.pnl.sum() / len(dd), 2))
