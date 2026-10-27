import pandas as pd, numpy as np
d = pd.read_csv('/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv')
d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
g = d.groupby(d.index.normalize())
last = g.apply(lambda x: x.index[-1].strftime('%H:%M')); first = g.apply(lambda x: x.index[0].strftime('%H:%M'))
s = pd.DataFrame({'first': first, 'last': last, 'n': g.size()})
s['dow'] = s.index.dayofweek
print(s.groupby([s.index < '2026-03-01', 'last']).size().sort_index().to_string())
# transition
chg = s[(s.index >= '2026-02-20') & (s.index <= '2026-03-20')]
print(chg.to_string())
print('first-bar counts', s['first'].value_counts().head(8).to_dict())
# days w/o 08:55
t = d.index.strftime('%H:%M')
has = pd.Series(t == '08:55', index=d.index).groupby(d.index.normalize()).any()
wk = has[has.index.dayofweek < 5]
print('days', len(wk), 'with 08:55', wk.sum(), 'missing:', list(wk[~wk].index.date))
rng = pd.Series((d.index.hour < 9), index=d.index).groupby(d.index.normalize()).sum()
rng = rng[rng.index.dayofweek < 5]
print('range bar counts lowest', rng.sort_values().head(12).to_dict())
