import sys
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
import pandas as pd, numpy as np
from lib import load
d = load('M5'); d = d[d.index.dayofweek < 5]
day = d.index.normalize()
g = d.groupby(day)
L = pd.DataFrame({'first': g.apply(lambda x: x.index[0]), 'last': g.apply(lambda x: x.index[-1]), 'n': g.size()})
x = L[(L.index >= '2025-05-01') & (L['first'].dt.hour == 0)]
print(x.to_string())
for dd in x.index[:4]:
    print(d.loc[str(dd.date())].head(16)[['open','high','low','close','spread']].to_string())
