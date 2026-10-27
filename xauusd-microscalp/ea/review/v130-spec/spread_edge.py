"""EA:797 / Ind:432 compare spread > pct/100*TP + point/2. At the defaults 50/100*0.25 + 0.01/2 = 0.13 exactly,
which is a price-grid value, so a 13-point spread (52% of TP) passes or fails on floating-point noise."""
import numpy as np, pandas as pd
lim = 50 / 100.0 * 0.25 + 0.01 / 2          # same operation order as the MQL5 code (double arithmetic)
print('limit + tolerance =', repr(lim), ' == 0.13 ?', lim == 0.13)
# Indicator: s = spread_points * _Point
s_ind = 13 * 0.01
print('indicator: 13 pts * 0.01 =', repr(s_ind), ' too wide?', s_ind > lim)
# EA: ask - bid, both quotes being the doubles nearest to 2-decimal prices
m = pd.read_csv('/mnt/project-files/xauusd-microscalp/data/XAUUSD_M1.csv', usecols=['close'])
bids = np.round(m.close.values, 2)
asks = np.array([float(f'{b + 0.13:.2f}') for b in bids])
spr = asks - bids
print('EA: 13-point spreads over', len(bids), 'real bid prices: rejected', int((spr > lim).sum()), ' passed', int((spr <= lim).sum()))
for pts in (12, 14):
    a = np.array([float(f'{b + pts/100:.2f}') for b in bids]); sp = a - bids
    print(f'  {pts} points: rejected {int((sp > lim).sum())}, passed {int((sp <= lim).sum())}')
print('price range', bids.min(), bids.max())
