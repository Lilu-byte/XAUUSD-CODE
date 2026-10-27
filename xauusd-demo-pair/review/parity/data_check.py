import sys; sys.dont_write_bytecode = True
import pandas as pd, numpy as np
d = pd.read_csv('/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv')
d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
print('range', d.index[0], d.index[-1], 'close min/max', d.close.min(), d.close.max())
g = d.groupby(d.index.normalize())
first = g.apply(lambda x: x.index[0].strftime('%H:%M')); last = g.apply(lambda x: x.index[-1].strftime('%H:%M'))
t = pd.DataFrame({'first': first, 'last': last})
t['dow'] = t.index.dayofweek
t['month'] = t.index.to_period('M')
print(t.groupby(['month', 'last']).size().unstack(fill_value=0).to_string())
print('first bar counts', t['first'].value_counts().head(8).to_dict())
print('days with last bar < 23:30 before 2026-03-01:', t[(t.index < '2026-03-01') & (t['last'] < '23:30')].index.strftime('%Y-%m-%d').tolist())
print('days with last bar >= 23:30 after 2026-03-01:', t[(t.index >= '2026-03-01') & (t['last'] >= '23:30')].index.strftime('%Y-%m-%d').tolist())
print('days with last bar < 22:45:', t[t['last'] < '22:45'][['first','last']].to_dict('index'))
print('weekend bars', (d.index.dayofweek >= 5).sum())
