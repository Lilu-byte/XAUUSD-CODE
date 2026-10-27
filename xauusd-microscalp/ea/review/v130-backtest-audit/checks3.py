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
st = V.score(T, H.dates, 'test')['per_day']; st_tr = V.score(T, H.dates, 'train')['per_day']
# 1) random baseline with many seeds (unrounded per-day)
def pdays(T, per):
    p = R.per_day(T, H.dates); return p[H.dates >= SPLIT].mean() if per == 'test' else p[H.dates < SPLIT].mean()
s_te, s_tr = pdays(T, 'test'), pdays(T, 'train')
rte, rtr = [], []
for z in range(500):
    Sr = {k: random_like(v, 100000 + z * 10 + i).astype(np.int64) for i, (k, v) in enumerate(S.items())}
    Tr, _ = V.run(H, tr, V.D, S=Sr); rte.append(pdays(Tr, 'test')); rtr.append(pdays(Tr, 'train'))
rte, rtr = np.array(rte), np.array(rtr)
print(f'strategy test {s_te:.3f}/day; random 500: median {np.median(rte):.3f}, mean {rte.mean():.3f}, sd {rte.std():.3f}, share random >= strategy {(rte >= s_te).mean():.3f}')
print(f'strategy train {s_tr:.3f}/day; random 500: median {np.median(rtr):.3f}, sd {rtr.std():.3f}, share random >= strategy {(rtr >= s_tr).mean():.3f}')
# 2) gross (pre-spread) move per trade and its t-stat
spr = H._spr['base']
for per, sel in (('train', T.entry < SPLIT), ('test', T.entry >= SPLIT)):
    g = T[sel]; x = g.pnl + spr[g.ei + 1]
    print(per, 'n', len(g), 'gross per trade', round(x.mean(), 4), 'sd', round(x.std(), 3), 't', round(x.mean() / x.std() * np.sqrt(len(x)), 2))
# 3) look-ahead check on the spread filter: filter on the SIGNAL bar's recorded spread (known before entry) instead of the entry bar's
def run_module_alt(s, tp, sl, hold, cap, pct, use='signal', perstop=False):
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
    seen = spread_series(m, 'bar'); nxt = np.r_[seen[1:], 99.0]
    f = seen if use == 'signal' else nxt
    lim = min(0.50, pct / 100.0 * tp)
    s = np.where((gap == 60) & (f <= lim + 1e-9), s, 0)
    sp = H._spr['base']
    slx = sl + float(np.median(np.r_[sp[1:], sp[-1]][s != 0]))
    dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, sp, H.tod, H.day, H.last, s, float(tp), float(slx), int(hold), int(cap), FILL['FAIR'], 0.0, 0.0, 0)
    return pd.DataFrame({'entry': m.index[ti], 'ei': ti, 'xi': np.where(to >= 0, to, ti), 'dir': tdr, 'pnl': tpn})
out = []
for k, s in S.items():
    t = run_module_alt(s, V.D['tp'], V.D['sl'], V.D['hold'][k], V.D['cap'][k], V.D['spread_pct'], use='signal'); t['module'] = k; out.append(t)
Ta = pd.concat(out).sort_values('entry')
print('filter on signal-bar spread: TRAIN', V.score(Ta, H.dates, 'train')); print('                             TEST ', V.score(Ta, H.dates, 'test'))
# 4) caps never bind? run with cap 1 for all
out = []
for k, s in S.items():
    t = V.run_module(H, s, V.D['tp'], V.D['sl'], V.D['hold'][k], 1, V.D['spread_pct']); t['module'] = k; out.append(t)
Tc = pd.concat(out)
print('cap=1 everywhere: trades', len(Tc), 'vs', len(T), ' pnl sum', round(Tc.pnl.sum(), 3), 'vs', round(T.pnl.sum(), 3))
# 5) sell vs buy split in test
te = T[T.entry >= SPLIT]
print('test by direction:', te.groupby('dir').pnl.agg(['count', 'mean']).round(3).to_dict())
# 6) move vs spread table as the script prints it
print(V.move_vs_spread(H, S).to_string(index=False))
