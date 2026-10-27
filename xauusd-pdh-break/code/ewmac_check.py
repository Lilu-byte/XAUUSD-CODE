"""EWMAC against holding the same average amount of gold (18 Oct 2026)."""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
import pdh as P, others as O
d = P.load('H1'); c = d.close
raw = (c.ewm(span=16, adjust=False).mean() - c.ewm(span=64, adjust=False).mean()) / c.diff().ewm(span=100, adjust=False).std()
u = pd.Series(np.round(np.clip(raw / 2.11, 0, 2) * 2), index=d.index).shift(1)
e = O.ewmac(); d1 = P.load('D1')
for a, b in (('2016-08-01', '2021-06-30'), ('2021-07-01', '2026-10-09'), ('2025-05-06', '2026-10-09'), ('2016-08-01', '2026-10-09')):
    nd = len(pd.bdate_range(a, b)); avg = u[a:b].mean(); x = d1[a:b].close
    hold1 = (x.iloc[-1] - x.iloc[0] - 0.4 - 0.126 * (x.index[-1] - x.index[0]).days) / nd
    s = e[a:b]; dd = s.groupby(s.index.normalize()).sum(); eq = dd.cumsum()
    hx = (x - x.iloc[0]) * avg; 
    print(f'{a}..{b}: avg units {avg:.2f} (time at 4 units {(u[a:b]==4).mean():.0%}, flat {(u[a:b]==0).mean():.0%}), '
          f'EWMAC $/day {s.sum()/nd:.2f}, holding the same avg size $/day {hold1*avg:.2f}; '
          f'dd EWMAC ${(eq-eq.cummax()).min():.0f} vs hold-same-size ${(hx-hx.cummax()).min():.0f}; units changes/day {(u[a:b].diff().abs()>0).sum()/nd:.2f}')
