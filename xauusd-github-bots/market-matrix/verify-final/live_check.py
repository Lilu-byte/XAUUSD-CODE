import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm
d1 = gbt.load('D1')
print('D1 first', d1.index[0], 'last', d1.index[-1], 'n', len(d1))
L = d1.low.values; H = d1.high.values
# thresholds for next 5 trading days: new 50-bar low needs low <= min of previous 49 bars
for i in range(1, 6):
    # day t+i: window of previous 49 bars includes (49 - (i-1)) known bars plus i-1 unknown future bars (assume higher)
    known = 49 - (i - 1)
    thr = L[-known:].min()
    print('day +%d threshold (min of last %d known lows) = %.2f' % (i, known, thr))
print('min last 50', L[-50:].min(), d1.index[-50 + np.argmin(L[-50:])])
print('lows last 55:', [(str(t.date()), round(v,2)) for t, v in zip(d1.index[-55:], L[-55:])])
hi50 = d1.high.rolling(50).max(); lo50 = d1.low.rolling(50).min()
print('last new 50d high', d1.index[np.where(H >= hi50.values)[0][-1]], 'last new 50d low', d1.index[np.where(L <= lo50.values)[0][-1]])
for tf in ['H4','H1']:
    d = gbt.load(tf); print(tf, 'last', d.index[-1], 'first', d.index[0])
h4 = gbt.load('H4')
p, _ = mm.all_panels(h4)
c = p.close
pos = np.where((c > p.sma20) & (p.sma20 > p.sma50) & (p.sma50 > p.sma200), 1, 0)
s = pd.Series(pos, h4.index)
ch = s[s.diff() != 0]
print('H4 MA stack LO last changes:', ch.tail(6).to_dict())
print('state since 2026-08-20:', s.loc['2026-08-20':].groupby(s.loc['2026-08-20':].index.normalize()).max().to_dict())
