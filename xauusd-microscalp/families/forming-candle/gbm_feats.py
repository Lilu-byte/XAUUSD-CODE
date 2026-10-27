"""Feature matrix for a combined forming-candle model. Every column at M1 row i uses only bars <= i."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from feats import *


def gbm_matrix(m1, X):
    Z = pd.DataFrame(index=m1.index)
    for p in ('f5', 'f15'):
        o, h, l, c, m = (X[p + k].values for k in 'ohlcm')
        ar = X[p + 'ar12'].values
        rg = h - l
        Z[p + '_min'] = m
        Z[p + '_bn'] = (c - o) / ar
        Z[p + '_rn'] = rg / ar
        Z[p + '_clv'] = np.where(rg > 0, (c - l) / np.where(rg > 0, rg, 1), .5)
        Z[p + '_lw'] = np.where(rg > 0, (np.minimum(o, c) - l) / np.where(rg > 0, rg, 1), 0)
        Z[p + '_uw'] = np.where(rg > 0, (h - np.maximum(o, c)) / np.where(rg > 0, rg, 1), 0)
        p1h, p1l = X[p + 'p1h'].values, X[p + 'p1l'].values
        pr = p1h - p1l
        Z[p + '_loc'] = np.where(pr > 0, (c - p1l) / np.where(pr > 0, pr, 1), .5)
        Z[p + '_brk'] = (h > p1h).astype(int) - (l < p1l).astype(int)
        for j in (1, 2, 3):
            po, ph, pl, pc = (X[f'{p}p{j}{k}'].values for k in 'ohlc')
            prg = ph - pl
            Z[f'{p}_p{j}bn'] = (pc - po) / ar
            Z[f'{p}_p{j}clv'] = np.where(prg > 0, (pc - pl) / np.where(prg > 0, prg, 1), .5)
        Z[p + '_vol'] = ar / X[p + 'ar48'].values
    # M1-level context
    rg1 = (m1.high - m1.low)
    a1 = rg1.rolling(30, min_periods=10).mean()
    Z['m1_bn'] = (m1.close - m1.open) / a1
    Z['m1_clv'] = np.where(rg1 > 0, (m1.close - m1.low) / rg1.where(rg1 > 0, 1), .5)
    for k in (1, 2, 3, 5):
        Z[f'r{k}'] = (m1.close - m1.close.shift(k)) / a1
    Z['a1'] = a1
    Z['spr'] = m1.spread_usd
    Z['moq'] = m1.tod % 15
    Z['moh'] = m1.tod % 60
    Z['hour'] = m1.tod // 60
    Z['tv'] = m1.tick_volume / m1.tick_volume.rolling(60, min_periods=20).mean()
    return Z
