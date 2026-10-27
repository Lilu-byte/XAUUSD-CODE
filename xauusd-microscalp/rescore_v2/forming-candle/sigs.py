"""Signal builders for the forming-candle family. Every signal at M1 bar i uses only bars <= i
(the forming candle as known at bar i's close, and candles that closed before it began)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from feats import *


def parts(X, p):
    o, h, l, c, m = (X[p + k].values for k in 'ohlcm')
    ar = X[p + 'ar12'].values
    rg = h - l
    bn = (c - o) / ar
    clv = np.where(rg > 0, (c - l) / np.where(rg > 0, rg, 1), .5)
    return o, h, l, c, m, ar, rg, bn, clv


def strong_close_fade(X, p='f15', thr=0.6, cl=0.9, minutes=(14, 15)):
    """Forming candle (minute in `minutes`) has body > thr * avg range of last 12 closed candles and
    the current close is in the top (bottom) (1-cl) of its range -> SELL (BUY): fade it."""
    o, h, l, c, m, ar, rg, bn, clv = parts(X, p)
    M = np.isin(m, minutes)
    bull = M & (bn > thr) & (clv >= cl); bear = M & (bn < -thr) & (clv <= 1 - cl)
    return np.where(bull, -1, np.where(bear, 1, 0))


def first_minute_break_fade(X, p='f15', minutes=(1,), mode='close', thr=0.0):
    """In the first minute(s) of a new candle the price is already beyond the previous closed candle's
    high (low) -> SELL (BUY). mode 'close': close beyond; 'touch': high/low beyond. thr: extra
    distance beyond, as a fraction of the average range."""
    o, h, l, c, m, ar, rg, bn, clv = parts(X, p)
    p1h, p1l = X[p + 'p1h'].values, X[p + 'p1l'].values
    M = np.isin(m, minutes)
    if mode == 'close':
        up = M & (c > p1h + thr * ar); dn = M & (c < p1l - thr * ar)
    else:
        up = M & (h > p1h + thr * ar); dn = M & (l < p1l - thr * ar)
    x = up ^ dn
    return np.where(x & up, -1, np.where(x & dn, 1, 0))
