"""TRAIN robustness of the London 'fade the M1 N-bar breakout' / 'sweep reversal' cluster:
by N, by hour of day, by week. TRAIN only."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from sigs2 import *
from mlib import Harness, spread_series
H = Harness(); m1 = H.m1; spr = spread_series(m1, 'base'); o, h, l, c = arrs(m1)
idx = m1.index; TR = idx < SPLIT; hr = idx.hour.values
F = {k: np.r_[c[k:] - c[:-k], np.full(k, np.nan)] for k in (1, 2, 3, 5, 10, 20)}
pd.set_option('display.width', 250)


def stat(s, msk, k):
    a = (F[k] * s)[msk & (s != 0)]; a = a[~np.isnan(a)]
    return a.mean(), len(a)


print('fade N-bar M1 breakout (s = -breakout): TRAIN move-minus-spread at 5m / 10m, by N and hour')
rows = []
for N in (10, 20, 30, 45, 60, 90, 120):
    s = -breakout(o, h, l, c, N).astype(float)
    r = {'N': N}
    for hh in range(1, 23):
        m = TR & (hr == hh) & (s != 0)
        mv, n = stat(s, m, 5)
        r[hh] = mv - spr[m].mean()
    rows.append(r)
print(pd.DataFrame(rows).set_index('N').round(2).to_string())

print('\nsweep_M1 loose reversal: TRAIN move5 minus spread by N and hour')
rows = []
for N in (3, 5, 10, 15, 30, 60):
    s = sweep(o, h, l, c, N).astype(float)
    r = {'N': N}
    for hh in range(1, 23):
        m = TR & (hr == hh) & (s != 0)
        mv, n = stat(s, m, 5)
        r[hh] = mv - spr[m].mean()
    rows.append(r)
print(pd.DataFrame(rows).set_index('N').round(2).to_string())

print('\nall-bar one-bar reversal (s = -sign(close-open)) TRAIN move-minus-spread by hour, k=1,5')
s = -np.sign(c - o)
for k in (1, 5):
    print(k, {hh: round(stat(s, TR & (hr == hh), k)[0] - spr[TR & (hr == hh)].mean(), 2) for hh in range(1, 23)})

print('\nweekly TRAIN move10 (no spread) for fade brk_M1_N30 in London 10-15h, and n')
s = -breakout(o, h, l, c, 30).astype(float)
lon = (m1.tod.values >= 600) & (m1.tod.values < 900)
m = TR & lon & (s != 0)
a = pd.Series((F[10] * s), index=idx)[m]
g = a.groupby(a.index.to_period('W'))
print(pd.DataFrame({'mv10': g.mean(), 'n': g.size()}).round(2).T.to_string())
a = pd.Series((F[5] * s), index=idx)[m]
g = a.groupby(a.index.to_period('W'))
print(pd.DataFrame({'mv5': g.mean()}).round(2).T.to_string())
