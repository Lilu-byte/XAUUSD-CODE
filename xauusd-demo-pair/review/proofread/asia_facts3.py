import sys
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
import pandas as pd, numpy as np
from lib import load
d = load('M5')
day = d.index.normalize()
g = d.groupby(day)
L = pd.DataFrame({'first': g.apply(lambda x: x.index[0].strftime('%H:%M')), 'last': g.apply(lambda x: x.index[-1].strftime('%H:%M')), 'n': g.size()})
L['dow'] = L.index.day_name().str[:3]
print(L.loc['2025-10-20':'2025-11-07'].to_string())
print(L.loc['2026-03-02':'2026-04-03'].to_string())
print(L.loc['2026-09-28':].to_string())
