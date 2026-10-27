import sys
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
import pandas as pd, numpy as np
from lib import load
d = load('M5'); d = d[d.index.dayofweek < 5]
tod = d.index.hour*60 + d.index.minute
day = d.index.normalize()
last = d.groupby(day).apply(lambda x: x.index[-1])
first = d.groupby(day).apply(lambda x: x.index[0])
L = pd.DataFrame({'first': first, 'last': last})
L['dow'] = L.index.dayofweek
rec = L[L.index >= '2026-03-12']
print('last bar tod by weekday since 2026-03-12:')
print(rec.groupby('dow')['last'].apply(lambda s: (s.dt.hour*60+s.dt.minute).value_counts().to_dict()))
print('first bar tod by weekday since 2026-03-12:')
print(rec.groupby('dow')['first'].apply(lambda s: (s.dt.hour*60+s.dt.minute).value_counts().to_dict()))
# spread of the first bars of the day
for dd in ['2025-05-27', '2025-09-02']:
    x = d.loc[dd].head(14)
    print(dd); print(x[['open','close','spread']].to_string())
# bars at 22:45 present?
has2245 = d[tod == 22*60+45].index.normalize().unique()
print('days without a 22:45 bar (since 2025-05-06):', [str(x.date()) for x in day.unique() if x >= pd.Timestamp('2025-05-06') and x not in has2245][:40])
