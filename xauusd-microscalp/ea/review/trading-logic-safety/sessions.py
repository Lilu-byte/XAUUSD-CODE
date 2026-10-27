import sys; sys.path.insert(0,'/mnt/project-files/xauusd-microscalp/code')
from mlib import *
m = load_m1()
g = m.groupby(m.index.normalize())
df = pd.DataFrame({'first': g.apply(lambda x: x.index[0].strftime('%H:%M')), 'last': g.apply(lambda x: x.index[-1].strftime('%H:%M')),
                   'n': g.size(), 'dow': [d.dayofweek for d in g.size().index]})
print(df['last'].value_counts().head(20)); print(df['first'].value_counts().head(10))
print(df[(df['last']!='22:59')|(df['first']!='01:00')])
# intraday gaps > 2 min within a day
idx = m.index.to_series(); gap = idx.diff()
big = gap[(gap > pd.Timedelta(minutes=2)) & (idx.dt.normalize()==idx.shift(1).dt.normalize())]
print('intraday gaps >2min:', len(big)); print(big.sort_values(ascending=False).head(15))
print('spread pts quantiles', m.spread.quantile([.5,.9,.95,.99]).to_dict(), 'frac>50', (m.spread>50).mean())
