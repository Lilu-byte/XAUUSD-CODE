import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
import ea_replica_v130 as V
from mlib import Harness, SPLIT, spread_series, FILL
from ea_sim import _sim_next
H = Harness(); tr = V.R.h1_trend(H.m1); m = H.m1
T, S = V.run(H, tr, V.D)
spr = H._spr['base']; bar = H._spr['bar']
gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
for use in ('entry', 'signal'):
    out = []
    for k, s in S.items():
        f = np.r_[bar[1:], 99.0] if use == 'entry' else bar
        s2 = np.where((gap == 60) & (f <= 0.125 + 1e-9), s, 0)
        slx = 0.6 + float(np.median(np.r_[spr[1:], spr[-1]][s2 != 0]))
        dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, spr, H.tod, H.day, H.last, s2, 0.25, slx, V.D['hold'][k], V.D['cap'][k], FILL['FAIR'], 0.0, 0.0, 0)
        out.append(pd.DataFrame({'entry': m.index[ti], 'ei': ti, 'pnl': tpn, 'dir': tdr}))
    X = pd.concat(out); X = X[X.entry >= SPLIT]
    ch = spr[X.ei + 1]
    print(use, 'test n', len(X), 'per trade', round(X.pnl.mean(), 3), 'charged spread', round(ch.mean(), 3), 'gross', round((X.pnl + ch).mean(), 3))
