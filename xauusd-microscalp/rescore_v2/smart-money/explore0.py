import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *
H = Harness(); m = H.m1
print(len(m), m.index[0], m.index[-1], 'days', len(H.dates), 'train days', (H.dates < SPLIT).sum())
print(m.spread_usd.describe())
r = m.high - m.low
print('range', r.describe())
print('by hour: median range, median spread, count')
g = m.groupby(m.index.hour)
print(pd.DataFrame({'rng': g.apply(lambda d: (d.high-d.low).median()), 'spr': g.spread_usd.median(), 'n': g.size()}).round(2).T.to_string())
# missing minutes within day
d = m.index.to_series().diff().dt.total_seconds().div(60)
print('gaps>1 min:', (d > 1).sum(), 'gaps>5:', (d > 5).sum())
