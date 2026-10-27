import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
from mlib import load_m1, SPLIT
m = load_m1()
raw = pd.read_csv('/mnt/project-files/xauusd-microscalp/data/XAUUSD_M1.csv', usecols=['time', 'spread'])
raw.index = pd.to_datetime(raw.time, format='%Y.%m.%d %H:%M'); raw = raw.spread.reindex(m.index)
ins = (m.tod >= 900) & (m.tod < 1140)
for per, sel in (('train', m.index < SPLIT), ('test', m.index >= SPLIT)):
    x = raw[sel & ins]
    print(per, 'session bars', len(x), 'recorded spread pts quantiles', x.quantile([.01, .05, .1, .25, .5, .75, .9]).to_dict())
    print('   share zero (replaced by hour median)', round((x <= 0).mean(), 3))
    vc = (m.spread_usd[sel & ins] * 100).round().value_counts().sort_index()
    print('   used (after zero replacement) pts counts:', vc.head(20).to_dict())
    print('   share <= 7 pts', round(((m.spread_usd[sel & ins]) <= 0.075 + 1e-9).mean(), 3), ' share <= 12 pts', round(((m.spread_usd[sel & ins]) <= 0.125 + 1e-9).mean(), 3), ' share == 13 pts', round(((m.spread_usd[sel & ins] * 100).round() == 13).mean(), 3))
# by month
x = raw[ins]
print(x.groupby(x.index.to_period('W')).median())
