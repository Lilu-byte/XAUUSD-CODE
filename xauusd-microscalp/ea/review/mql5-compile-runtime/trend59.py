# How often does the indicator's TrendAt (iBarShift(t-1)+1) disagree with the EA/Python H1 trend on PB signals?
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
sys.path.insert(0, '/mnt/project-files/xauusd-candles/code')
from mlib import *
from ea_replica import h1_trend, sig_pullback
m = load('M1'); tr = h1_trend(m)
# indicator: for an M1 bar at hh:59, it uses the H1 bar one hour older -> equals Python's trend one minute earlier (hh:58)
tr_ind = tr.copy()
is59 = m.index.minute == 59
prev = pd.Series(tr, index=m.index).shift(1).values
tr_ind[is59] = prev[is59]
a = sig_pullback(m, tr); b = sig_pullback(m, tr_ind)
print('PB signals python', int((a != 0).sum()), 'indicator', int((b != 0).sum()), 'differ', int((a != b).sum()),
      'of which at :59', int(((a != b) & is59).sum()), 'trend differs at :59 bars', int((tr != tr_ind).sum()))
