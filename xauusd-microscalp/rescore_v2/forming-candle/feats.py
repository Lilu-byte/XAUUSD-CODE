"""Forming-candle features on the M1 timeline (all known at the M1 bar's close; no look-ahead).

For each M1 row i: the partial M5/M15 candle (forming), the previous 1..3 CLOSED candles of that
timeframe, recent average closed-candle range, and forward bid moves (for TRAIN-only edge scans).
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *

FC = '/mnt/project-files/xauusd-microscalp/families/forming-candle/'


def tf_feats(m1, minutes, pre):
    f = forming(m1, minutes)
    key = m1.index.floor(f'{minutes}min')
    r = resample(m1, minutes)                      # closed candles, label = open time
    pos = r.index.get_indexer(key)                 # position of the forming candle in r
    assert (pos >= 0).all()
    rng = (r.high - r.low).values
    body = (r.close - r.open).values
    out = pd.DataFrame(index=m1.index)
    out[pre + 'o'] = f.f_open.values; out[pre + 'h'] = f.f_high.values
    out[pre + 'l'] = f.f_low.values; out[pre + 'c'] = f.f_close.values
    out[pre + 'm'] = f.f_minute.values
    # previous closed candles (positions pos-1, pos-2, pos-3): all closed before the forming one began
    for j in (1, 2, 3):
        p = pos - j
        ok = p >= 0
        pp = np.where(ok, p, 0)
        for col, arr in (('o', r.open.values), ('h', r.high.values), ('l', r.low.values), ('c', r.close.values)):
            out[f'{pre}p{j}{col}'] = np.where(ok, arr[pp], np.nan)
    # average range of the last N closed candles (ending at pos-1)
    for n in (12, 48):
        ar = pd.Series(rng).rolling(n, min_periods=n // 2).mean().values   # ar[q] = mean range of candles q-n+1..q
        p = pos - 1
        out[f'{pre}ar{n}'] = np.where(p >= 0, ar[np.maximum(p, 0)], np.nan)
    # was the previous forming high/low (one M1 earlier, same candle) below/above the prev candle's high/low?
    same = np.r_[False, key[1:] == key[:-1]]
    out[pre + 'h_prev'] = np.where(same, np.r_[np.nan, out[pre + 'h'].values[:-1]], np.nan)
    out[pre + 'l_prev'] = np.where(same, np.r_[np.nan, out[pre + 'l'].values[:-1]], np.nan)
    return out


def build(m1):
    X = pd.concat([tf_feats(m1, 5, 'f5'), tf_feats(m1, 15, 'f15')], axis=1)
    X['o1'] = m1.open; X['h1'] = m1.high; X['l1'] = m1.low; X['c1'] = m1.close
    X['spr'] = spread_series(m1, 'base')
    X['tod'] = m1.tod
    X['hour'] = m1.index.hour
    X['train'] = m1.index < SPLIT
    # first/second half of TRAIN for stability checks
    X['half'] = np.where(m1.index < pd.Timestamp('2026-08-01'), 0, 1)
    return X


def fwd(m1, ks=(1, 2, 3, 5, 10)):
    """Forward bid-close moves; NaN if the window crosses a time gap (not k consecutive minutes)."""
    c = m1.close.values
    t = m1.index.values.astype('datetime64[m]').astype(np.int64)
    out = {}
    for k in ks:
        f = np.full(len(c), np.nan)
        f[:-k] = c[k:] - c[:-k]
        gap = np.full(len(c), True)
        gap[:-k] = (t[k:] - t[:-k]) != k
        f[gap] = np.nan
        out[k] = f
    return out
