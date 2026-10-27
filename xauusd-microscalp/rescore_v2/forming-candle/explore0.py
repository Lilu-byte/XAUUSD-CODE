import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *
import time
t=time.time()
H = Harness(); m=H.m1
print(len(m), m.index[0], m.index[-1], time.time()-t)
print(m.spread_usd.describe())
print((m.spread==0).mean())
tr = m.index<SPLIT
print('train days', len(np.unique(m.index[tr].date)), 'test days', len(np.unique(m.index[~tr].date)))
f=forming(m,5)
print(f.head(12))
print(f.f_minute.value_counts().sort_index())
# spread by hour
print(m.groupby(m.index.hour).spread_usd.mean().round(3).to_dict())
print((m.high-m.low).groupby(m.index.hour).median().round(2).to_dict())
