import pandas as pd, numpy as np
d = pd.read_csv('/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv')
d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
g = d.groupby(d.index.normalize())
s = pd.DataFrame({'first': g.apply(lambda x: x.index[0].strftime('%H:%M')), 'last': g.apply(lambda x: x.index[-1].strftime('%H:%M')), 'n': g.size()})
s['dow'] = s.index.dayofweek
p = s[s.index >= '2026-03-09']
print(p.groupby(['first']).size().to_dict())
print(p[p['first'] == '00:00'].index.date[[0, -1]], p[(p.index > '2026-03-25')].head(8).to_string())
print(s[s['last'] == '23:50'].dow.value_counts().to_dict())
print(s.loc['2025-07-02':'2025-07-07'].to_string())
print(s[s['last'] < '22:55'].to_string())
