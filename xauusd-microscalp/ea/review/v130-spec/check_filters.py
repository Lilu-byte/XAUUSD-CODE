"""Spec-compliance lens: does each v1.30 default filter actually bind, and do the position caps bind?"""
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
tod = m.tod.values
ins = (tod >= 900) & (tod < 1140)
hours = (tod >= 65) & (tod <= 1349)
ndays = len(np.unique(H.day))
print('days', ndays)

for b in (0.0, 0.5, 0.8):
    pb = V.pb_signal(m, tr, body_min=b)
    cp = V.cp_signal(m, tr, V.CP_DEFAULT, b)
    print(f'body_min {b}: PB signals in session {int((pb!=0)[ins].sum())}  all-hours {int((pb!=0)[hours].sum())} | '
          f'CP in session {int((cp!=0)[ins].sum())}  all-hours {int((cp!=0)[hours].sum())}')

# PB: how close is body>=1.0*avgBody to body>=0.5*avgRange? share of 2-min candles where avg body >= 0.5 avg range
from mlib import resample
c = resample(m, 2)
body = (c.close - c.open).abs(); rng = c.high - c.low
avg = body.shift(1).rolling(20).mean(); avgr = rng.shift(1).rolling(20).mean()
print('PB 2-min: median avgBody/avgRange', round(float((avg/avgr).median()), 3),
      ' share of candles where 1.0*avgBody >= 0.5*avgRange', round(float((avg >= 0.5*avgr).mean()), 3))

# Caps: with the v1.30 signals (session, body, CP patterns) and the recorded-spread filter, count signals that come
# while the module already had cap signals inside its hold window (upper bound on open positions: every trade held to timeout)
S = V.signals(H, tr, V.D)
gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
rec = spread_series(m, 'bar'); nxt = np.r_[rec[1:], 99.0]
lim = 0.5 * 0.25
tmin = (m.index.values.astype('datetime64[m]').astype(np.int64))
allev = []
for k, s in S.items():
    s = np.where((gap == 60) & (nxt <= lim + 1e-9) & hours, s, 0)
    idx = np.where(s != 0)[0]
    hold = V.D['hold'][k]; cap = V.D['cap'][k]
    t = tmin[idx] + 1
    over = 0; maxopen = 0
    for j in range(len(idx)):
        openn = int(((t[:j] > t[j] - hold) & (t[:j] <= t[j])).sum())
        maxopen = max(maxopen, openn)
        if openn >= cap: over += 1
    print(f'{k}: entries {len(idx)} ({len(idx)/ndays:.1f}/day)  hold {hold}  cap {cap}  max open (upper bound) {maxopen}  blocked by cap {over}')
    allev += [(tt, hold) for tt in t]
allev.sort()
ts = np.array([a for a, _ in allev]); hs = np.array([b for _, b in allev])
mx = 0; blk = 0
for j in range(len(ts)):
    o = int(((ts[:j] + hs[:j] > ts[j]) & (ts[:j] <= ts[j])).sum())
    mx = max(mx, o); blk += o >= 12
print('total: max open (upper bound)', mx, ' blocked by the 12 cap', blk)

# spread limit at 40% vs 50% of TP: share of in-session entry bars whose recorded spread passes
for pct in (40, 50):
    l = pct / 100 * 0.25
    print(f'spread limit {pct}% (${l:.3f}): share of in-session bars with recorded spread <= limit', round(float((rec[ins] <= l + 1e-9).mean()), 3))
