import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
import ea_replica_v130 as V
from mlib import Harness, SPLIT, random_like, spread_series, FILL
from ea_sim import _sim_next
R = V.R
H = Harness(); tr = R.h1_trend(H.m1); m = H.m1
print('price: Jun26', m.close.iloc[0], 'Sep1 first', m.close[m.index >= SPLIT].iloc[0], 'last', m.close.iloc[-1])
T, S = V.run(H, tr, V.D)
# how many trades resolve with TP and stop both inside one bar (FAIR blend => pnl = -spread exactly)?
spr = H._spr['base']
for per, sel in (('train', T.entry < SPLIT), ('test', T.entry >= SPLIT)):
    g = T[sel]
    exact = np.isclose(g.pnl.values, -np.where(g.dir.values == 1, spr[g.ei.values + 1], spr[g.xi.values]), atol=1e-9)
    print(per, 'trades', len(g), 'share with pnl exactly -spread (FAIR both-hit blend)', round(exact.mean(), 3),
          ' exit on entry bar', round((g.xi == g.ei + 1).mean(), 3), ' pnl==tp', round(np.isclose(g.pnl, 0.25).mean(), 3))
# time exit only (no bracket): same entries, TP/SL out of reach
def run_noexit(H, s, hold, cap, pct=50, tp=0.25):
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
    nxt = np.r_[spread_series(m, 'bar')[1:], 99.0]
    s = np.where((gap == 60) & (nxt <= min(0.5, pct / 100 * tp) + 1e-9), s, 0)
    dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, H._spr['base'], H.tod, H.day, H.last, s, 1000.0, 1000.0, int(hold), int(cap), FILL['FAIR'], 0.0, 0.0, 0)
    return pd.DataFrame({'entry': m.index[ti], 'ei': ti, 'pnl': tpn, 'dir': tdr})
for hold_override in (None, 1, 2, 3, 5):
    out = []
    for k, s in S.items():
        h = V.D['hold'][k] if hold_override is None else hold_override
        t = run_noexit(H, s, h, V.D['cap'][k]); t['module'] = k; out.append(t)
    Tn = pd.concat(out)
    for per, sel in (('train', Tn.entry < SPLIT), ('test', Tn.entry >= SPLIT)):
        g = Tn[sel]; x = g.pnl; gross = x + spr[g.ei + 1]
        print(f'time exit only, hold {hold_override or "EA"}: {per} n {len(g)} per trade {x.mean():+.3f} gross {gross.mean():+.3f} t {gross.mean() / gross.std() * np.sqrt(len(g)):.2f}')
    if hold_override is None:
        for k, g in Tn[Tn.entry >= SPLIT].groupby('module'): print('     test', k, len(g), round(g.pnl.mean(), 3))
# same random-direction check for the time-exit version
