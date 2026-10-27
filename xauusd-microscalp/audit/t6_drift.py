"""Decompose total price change into intrabar moves, intraday bar-boundary gaps, and session-break gaps."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
import mlib
m1 = mlib.load_m1(); H = mlib.Harness(m1)
o, c = m1.open.values, m1.close.values
intrabar = (c - o)
g = o[1:] - c[:-1]
newday = H.day[1:] != H.day[:-1]
print('total change last close - first open: %.2f' % (c[-1] - o[0]))
print('sum intrabar (c-o): %.2f   mean/bar %.4f' % (intrabar.sum(), intrabar.mean()))
print('sum intraday open-gaps: %.2f  mean %.5f' % (g[~newday].sum(), g[~newday].mean()))
print('sum session-break gaps: %.2f  mean %.2f  (n=%d)' % (g[newday].sum(), g[newday].mean(), newday.sum()))
print('session-break gaps:', np.round(g[newday], 2).tolist())
# by hour, intrabar drift
print('mean intrabar c-o by hour:', pd.Series(intrabar, index=m1.index).groupby(m1.index.hour).mean().round(4).to_dict())
# daily session move (first open to last close of a day)
d = pd.DataFrame({'o': o, 'c': c, 'day': H.day})
dd = d.groupby('day').agg(o=('o', 'first'), c=('c', 'last'))
print('mean session move (day first open -> last close): %.2f, positive days %.2f' % ((dd.c - dd.o).mean(), ((dd.c - dd.o) > 0).mean()))
# compare to H1/D1 files if present
import os
for p in mlib.OTHER.values():
    print(p, os.path.exists(p))
