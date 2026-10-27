import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *
H = Harness(); m = H.m1
tr = m[m.index < SPLIT]
print(len(m), len(tr), m.index[0], m.index[-1])
print('train days', len(np.unique(tr.index.date)))
r1 = tr.close.diff()
print('r1 std', r1.std(), 'abs median', r1.abs().median())
for k in (1,2,3,5,10):
    f = tr.close.shift(-k) - tr.close
    print('lag1 autocorr r1 vs fwd', k, np.corrcoef(r1.fillna(0)[:-k], f.fillna(0)[:-k])[0,1])
print('spread_usd quantiles', tr.spread_usd.quantile([.1,.25,.5,.75,.9,.99]).round(3).to_dict())
print('gaps in index (>1min) count', (tr.index.to_series().diff() > pd.Timedelta(minutes=1)).sum())
print(tr.groupby(tr.index.hour).spread_usd.mean().round(3).to_dict())
