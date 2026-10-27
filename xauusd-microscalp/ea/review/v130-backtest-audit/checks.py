import sys, itertools
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
import ea_replica_v130 as V
from mlib import Harness, SPLIT, random_like, spread_series, FILL
from ea_sim import _sim_next
R = V.R
H = Harness(); tr = R.h1_trend(H.m1); m = H.m1
T, S = V.run(H, tr, V.D)
te = T[T.entry >= SPLIT]
spr = H._spr['base']; bar = H._spr['bar']
print('test trades', len(te), 'avg base spread charged at entry', round(spr[te.ei + 1].mean(), 4), 'avg recorded', round(bar[te.ei + 1].mean(), 4))
print('test per trade', round(te.pnl.mean(), 4), ' per trade + spread charged', round((te.pnl + spr[te.ei + 1]).mean(), 4))
tn = T[T.entry < SPLIT]
print('train trades', len(tn), 'avg base spread', round(spr[tn.ei + 1].mean(), 4), 'per trade', round(tn.pnl.mean(), 4), 'per trade + spread', round((tn.pnl + spr[tn.ei + 1]).mean(), 4))
raw = pd.read_csv('/mnt/project-files/xauusd-microscalp/data/XAUUSD_M1.csv', usecols=['time', 'spread'])
raw.index = pd.to_datetime(raw.time, format='%Y.%m.%d %H:%M'); raw = raw.spread.reindex(m.index).values
z = raw[tn.ei + 1] <= 0
print('train trades whose entry bar recorded spread 0 (imputed):', z.sum(), 'of', len(tn), ' trades/day without them', round((~z).sum() / (H.dates < SPLIT).sum(), 2), ' per trade without them', round(tn.pnl[~z].mean(), 4))
# trades per week in test
print('test trades per day by week:'); wk = te.groupby(te.entry.dt.to_period('W')).size(); dd = pd.Series(1, index=H.dates[H.dates >= SPLIT]).groupby(H.dates[H.dates >= SPLIT].to_period('W')).size()
print((wk / dd).round(2).to_dict())
# slx used
for k, s in S.items():
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
    nxt = np.r_[bar[1:], 99.0]
    s2 = np.where((gap == 60) & (nxt <= 0.125 + 1e-9), s, 0)
    print(k, 'slx', round(0.6 + float(np.median(np.r_[spr[1:], spr[-1]][s2 != 0])), 3), 'signals', (s != 0).sum(), 'pass filter', (s2 != 0).sum())
# concurrency across modules (EA total cap 12)
ev = []
for ei, xi in zip(T.ei, T.xi): ev.append((ei + 1, 1)); ev.append((xi + 1, -1))
ev.sort(key=lambda x: (x[0], x[1])); c = 0; mx = 0
for t, d in ev: c += d; mx = max(mx, c)
print('max concurrent positions across modules', mx)
# per-module max concurrent
for k, g in T.groupby('module'):
    ev = sorted([(a + 1, 1) for a in g.ei] + [(b + 1, -1) for b in g.xi], key=lambda x: (x[0], x[1])); c = mx = 0
    for t, d in ev: c += d; mx = max(mx, c)
    print('  ', k, 'max concurrent', mx, 'cap', V.D['cap'][k])
# 13-point spreads: how many extra signals would the EA (FP coin flip at 13 pts) let through
for k, s in S.items():
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
    nxt = np.r_[bar[1:], 99.0]
    e13 = ((s != 0) & (gap == 60) & (np.abs(nxt - 0.13) < 1e-6) & (m.index >= SPLIT)).sum()
    print(k, 'test signals with entry-bar spread exactly 13 pts', e13)
