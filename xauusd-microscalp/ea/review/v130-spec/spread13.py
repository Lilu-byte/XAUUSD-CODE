import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-candles/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
from mlib import Harness, spread_series
import ea_replica as R
import ea_replica_v130 as V
H = Harness(); m = H.m1; tr = R.h1_trend(m)
raw = m.spread.values                                  # recorded points (0 replaced? raw column is points)
t = m.tod.values; ins = (t >= 900) & (t < 1140)
vals, cnt = np.unique(raw[ins], return_counts=True)
print('in-session recorded spread (points): share', {int(v): round(c / ins.sum(), 3) for v, c in zip(vals, cnt) if 8 <= v <= 16})
S = V.signals(H, tr, V.D)
gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
nxtp = np.r_[raw[1:], 999]
hours = (t >= 65) & (t <= 1349)
tot12 = tot13 = 0
for k, s in S.items():
    base = (s != 0) & (gap == 60) & hours
    a = int((base & (nxtp <= 12)).sum()); b = int((base & (nxtp == 13)).sum())
    tot12 += a; tot13 += b
    print(f'{k}: signals with entry-bar recorded spread <=12 pts {a}, ==13 pts {b}')
print(f'ALL: <=12 pts {tot12}, ==13 pts {tot13}  -> indicator marks {tot12 + tot13}, replica/intended {tot12}')
