import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
from mlib import load, resample
m = load('M1')
for tf, n in (('M5', 5), ('H1', 60)):
    x = load(tf); r = resample(m, n)
    j = x.join(r, rsuffix='_r', how='inner')
    print(tf, 'common bars', len(j))
    for c in ('open', 'high', 'low', 'close'):
        d = (j[c] - j[c + '_r']).abs()
        print('  ', c, 'exact share', round((d < 0.005).mean(), 4), 'median abs diff', round(d.median(), 3))
    # check offsets: shift resampled by +-1 bar and compare closes
    for sh in (-1, 1):
        rr = r.copy(); rr.index = rr.index + pd.Timedelta(minutes=n * sh)
        jj = x.join(rr, rsuffix='_r', how='inner')
        print('   shift', sh, 'close exact share', round(((jj.close - jj.close_r).abs() < 0.005).mean(), 4))
