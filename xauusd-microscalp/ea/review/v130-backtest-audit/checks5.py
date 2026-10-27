import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
import ea_replica_v130 as V
from mlib import Harness, SPLIT, random_like, spread_series, FILL
from ea_sim import _sim_next
R = V.R
H = Harness(); tr = R.h1_trend(H.m1); m = H.m1
T, S = V.run(H, tr, V.D)
o, c = H.o, H.c; spr = H._spr['base']
def timeexit(T):
    h = T.module.map(V.D['hold']).values; ei = T.ei.values
    return T.dir.values * (c[ei + h] - o[ei + 1]) - np.where(T.dir.values == 1, spr[ei + 1], spr[ei + h])
for per, sel in (('train', T.entry < SPLIT), ('test', T.entry >= SPLIT)):
    g = T[sel]; x = timeexit(g)
    d = pd.Series(x, index=g.entry.dt.normalize()).groupby(level=0).sum()
    print(f'{per}: same entries, close after hold (no TP/SL): mean {x.mean():+.3f} median {np.median(x):+.3f} 10%-trimmed {pd.Series(x).sort_values().iloc[len(x)//10: -len(x)//10].mean():+.3f}; per day {d.mean():+.2f}, day-clustered t {d.mean()/d.std()*np.sqrt(len(d)):.2f}')
# random-direction baseline for the time-exit version, same bars
rte = []
for z in range(500):
    Sr = {k: random_like(v, 7000 + z * 10 + i).astype(np.int64) for i, (k, v) in enumerate(S.items())}
    Tr, _ = V.run(H, tr, V.D, S=Sr); g = Tr[Tr.entry >= SPLIT]; rte.append(timeexit(g).mean())
g = T[T.entry >= SPLIT]; s0 = timeexit(g).mean()
print(f'time-exit test per trade {s0:+.3f}; random 500 median {np.median(rte):+.3f}, share random >= strategy {(np.array(rte) >= s0).mean():.3f}')
# bracket sim under the OHLC fill model and STOP model for comparison
for fill in ('OHLC', 'STOP', 'TARGET'):
    out = []
    for k, s in S.items():
        gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
        nxt = np.r_[spread_series(m, 'bar')[1:], 99.0]
        s2 = np.where((gap == 60) & (nxt <= 0.125 + 1e-9), s, 0)
        slx = 0.6 + float(np.median(np.r_[spr[1:], spr[-1]][s2 != 0]))
        dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, spr, H.tod, H.day, H.last, s2, 0.25, slx, V.D['hold'][k], V.D['cap'][k], FILL[fill], 0.0, 0.0, 0)
        out.append(pd.DataFrame({'entry': m.index[ti], 'pnl': tpn}))
    Tf = pd.concat(out)
    print(fill, 'test per trade', round(Tf[Tf.entry >= SPLIT].pnl.mean(), 3), 'train', round(Tf[Tf.entry < SPLIT].pnl.mean(), 3))
