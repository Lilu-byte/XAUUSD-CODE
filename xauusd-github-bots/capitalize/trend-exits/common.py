"""Entries, exits and baselines shared by the grid and the final scoring (H1/H4/D1 MT5 bid data)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code'); sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/trend-exits')
import numpy as np, pandas as pd, gbt, tx
from gbt import load, htf, ema, sma, atr

TRAIN = ('2016-07-29', '2022-01-01'); TEST = ('2022-01-01', '2026-10-10'); COMMON = ('2025-05-05', '2026-10-10')


def d1_regime(d, n=200):
    """True while the last CLOSED D1 close is above its n-day SMA."""
    D = load('D1')
    return htf(d, 'D1', (D.close > sma(D.close, n)).astype(float).values) > 0.5


def maxi_sig(d, N=40, ob=75, os_=25, long_only=True):
    """Maxi0-912 entry (as in bots.maxi): close beyond prior N-bar high/low, EMA200 side, SMA-RSI(14), ATR>=30th pct of 500."""
    c = d.close; dd = c.diff()
    r = 100 - 100 / (1 + dd.clip(lower=0).rolling(14).mean() / (-dd).clip(lower=0).rolling(14).mean())
    a = atr(d, 14); q = a.rolling(500).quantile(0.30)
    hh = d.high.shift().rolling(N).max(); ll = d.low.shift().rolling(N).min(); e = ema(c, 200)
    ok = a >= q
    lng = ok & (c > hh) & (c > e) & (r < ob)
    sht = ok & (c < ll) & (c < e) & (r > os_)
    return np.where(lng, 1, 0 if long_only else np.where(sht, -1, 0)).astype(float)


def dc_sig(d, N, long_only=True):
    hh = d.high.shift().rolling(N).max(); ll = d.low.shift().rolling(N).min()
    return np.where(d.close > hh, 1, 0 if long_only else np.where(d.close < ll, -1, 0)).astype(float)


def ema_cross_sig(d, f, s, long_only=True):
    ef, es = ema(d.close, f), ema(d.close, s)
    up = (ef > es) & (ef.shift() <= es.shift()); dn = (ef < es) & (ef.shift() >= es.shift())
    return np.where(up, 1, 0 if long_only else np.where(dn, -1, 0)).astype(float)


def exits(d, kind, p):
    """Return tsim kwargs for an exit design. ATR(14) for stops; kind in fixed/chand/chan/ma."""
    a = atr(d, 14)
    if kind == 'fixed':           # Maxi original: SL 2 ATR, TP 2x SL
        return dict(sl=2 * a, tp=4 * a)
    if kind == 'chand':           # initial stop 2 ATR, chandelier trail p ATR(14) from best price since entry
        return dict(sl=2 * a, trail_m=p)
    if kind == 'chan':            # initial stop 2 ATR, exit on a close below the prior p-bar low (above p-bar high for shorts)
        return dict(sl=2 * a, exit_long=(d.close < d.low.shift().rolling(p).min()).values,
                    exit_short=(d.close > d.high.shift().rolling(p).max()).values)
    if kind == 'ma':              # initial stop 2 ATR, exit on a close below EMA(p)
        e = ema(d.close, p)
        return dict(sl=2 * a, exit_long=(d.close < e).values, exit_short=(d.close > e).values)
    raise ValueError(kind)


def hold_gold(d, start, end):
    """Buy 0.01 lot at the first open of the window, sell at the last close; swap every night (triple Wed)."""
    w = d[(d.index >= pd.Timestamp(start)) & (d.index < pd.Timestamp(end))]
    days = pd.DatetimeIndex(np.unique(w.index.normalize()))
    nights = 0.0
    dn = days.dayofweek
    for k in range(1, len(days)):
        nights += 3.0 if dn[k - 1] == 2 else 1.0
    g = w.close.iloc[-1] - (w.open.iloc[0] + gbt.SPREAD + gbt.SLIP)
    return dict(gross=round(g, 0), swap=round(nights * gbt.SWAP_L, 0), per_day=round((g - nights * gbt.SWAP_L) / len(days), 2),
                per_day_noswap=round(g / len(days), 2), days=len(days))


def hold_by_year(d):
    out = {}
    for y in sorted(set(d.index.year)):
        out[y] = hold_gold(d, f'{y}-01-01', f'{y+1}-01-01')['per_day']
    return out
