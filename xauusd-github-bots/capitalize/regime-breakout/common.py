"""Shared helpers for the regime-gated H1 breakout study (Approach A).
Engine, data and costs come from ../../code/gbt.py (not edited). Everything here only reads data.
Regimes are decided on CLOSED D1 bars (MT5 D1, from 2004) and reach H1 bars through gbt.htf(), so an
H1 bar only sees the regime of the last D1 bar that had fully closed before that H1 bar opened.
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
from gbt import load, htf, ema, sma, atr, adx, simulate, daily, stats, coinflip, SWAP_L  # noqa: F401
import bots

P = '/mnt/project-files/'
TRAIN = ('2016-07-29', '2021-12-31')
TEST = ('2022-01-01', '2026-10-31')
COMMON = ('2025-05-05', '2026-10-31')


# ---------------- regimes on D1 (value per D1 bar; +1 long allowed, -1 short allowed, 0 neither) -------------
def d1_regimes(D=None):
    D = load('D1') if D is None else D
    c = D.close
    s200 = sma(c, 200)
    ma = np.where((c > s200) & (s200 > s200.shift(20)), 1, np.where((c < s200) & (s200 < s200.shift(20)), -1, 0))
    m12 = np.sign(c / c.shift(252) - 1)
    m6 = np.sign(c / c.shift(126) - 1)
    ad, pdi, mdi = adx(D, 14)
    adxr = np.where(ad >= 25, np.sign(pdi - mdi), 0)
    a20 = atr(D, 20); vol = (a20 >= a20.rolling(250).median()).astype(float)   # direction-neutral gate
    both = np.where((ma == 1) & (m12 == 1), 1, np.where((ma == -1) & (m12 == -1), -1, 0))
    r = pd.DataFrame({'MA200': ma, 'MOM12': m12, 'MOM6': m6, 'ADX25': adxr, 'VOL': vol, 'MA+MOM12': both},
                     index=D.index).fillna(0)
    return r


def gate(d, sig, regime_name, long_only=False, R=None):
    """Keep an entry signal only where the closed-D1 regime allows its direction."""
    R = d1_regimes() if R is None else R
    sig = np.asarray(sig, float).copy()
    if regime_name != 'NONE':
        g = np.nan_to_num(htf(d, 'D1', R[regime_name].values))
        if regime_name == 'VOL':
            sig = np.where(g > 0, sig, 0)
        else:
            sig = np.where(((sig > 0) & (g > 0)) | ((sig < 0) & (g < 0)), sig, 0)
    if long_only:
        sig = np.where(sig > 0, sig, 0)
    return sig


# ---------------- base breakouts (H1) ----------------
def base(name, d=None):
    """Returns d, sig, kw. d can be another H1 frame (e.g. OANDA) with the same columns."""
    if name == 'MAXI':
        if d is None:
            return bots.maxi()
        c = d.close; dd = c.diff()
        r = 100 - 100 / (1 + dd.clip(lower=0).rolling(14).mean() / (-dd).clip(lower=0).rolling(14).mean())
        a = atr(d, 14); q = a.rolling(500).quantile(0.30)
        hh = d.high.shift().rolling(40).max(); ll = d.low.shift().rolling(40).min(); e = ema(c, 200)
        ok = a >= q
        sig = np.where(ok & (c > hh) & (c > e) & (r < 75), 1, np.where(ok & (c < ll) & (c < e) & (r > 25), -1, 0))
        return d, sig, dict(sl=2 * a, tp=4 * a)
    if name == 'DON':
        if d is None:
            return bots.donchian()
        a = atr(d, 48)
        hh = d.high.shift().rolling(120).max(); ll = d.low.shift().rolling(120).min()
        xh = d.high.shift().rolling(60).max(); xl = d.low.shift().rolling(60).min()
        sig = np.where(d.close > hh, 1, np.where(d.close < ll, -1, 0))
        return d, sig, dict(sl=2.5 * a, exit_long=(d.close < xl).values, exit_short=(d.close > xh).values)
    raise ValueError(name)


# ---------------- scoring ----------------
def window_daily(t, d, a, b):
    p = daily(t, d)
    return p[(p.index >= pd.Timestamp(a)) & (p.index <= pd.Timestamp(b))]


def summarize(p, t=None):
    eq = p.cumsum(); m = p.groupby(p.index.to_period('M')).sum()
    out = dict(per_day=round(p.mean(), 2), total=round(p.sum(), 0), max_dd=round((eq - eq.cummax()).min(), 0),
               losing_months=f'{(m < 0).sum()}/{len(m)}', days=len(p))
    if t is not None:
        out.update(trades=len(t), win=round((t.pnl > 0).mean() * 100, 1) if len(t) else np.nan,
                   pf=round(t.pnl[t.pnl > 0].sum() / max(1e-9, -t.pnl[t.pnl < 0].sum()), 2) if len(t) else np.nan)
    return out


def trades_in(t, a, b):
    return t[(t.exit_time >= pd.Timestamp(a)) & (t.exit_time <= pd.Timestamp(b) + pd.Timedelta(days=1))]


def years(p):
    return p.groupby(p.index.year).mean().round(2)


# ---------------- the pair (GoldAllAgree + GoldAsiaBreak replays) ----------------
def pair_daily():
    m5 = load('M5'); days = pd.DatetimeIndex(np.unique(m5.index.normalize()))
    a = pd.read_csv(P + 'xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
    b = pd.read_csv(P + 'xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
    pa = a.groupby(a.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0.0)
    pb = b.groupby(b.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0)
    return days, pa + pb, a, b


def max_open(intervals):
    """intervals: list of (start, end) Timestamps; returns max number open at once and when."""
    ev = []
    for s, e in intervals:
        ev.append((s, 1)); ev.append((e, -1))
    ev.sort(key=lambda x: (x[0], x[1]))   # close before open at the same stamp
    k = best = 0; when = None
    for ts, x in ev:
        k += x
        if k > best: best, when = k, ts
    return best, when


def hold_per_day(d, a, b):
    """Hold 0.01 lot from first open to last close in [a, b], paying long swap (triple Wed night)."""
    x = d[(d.index >= pd.Timestamp(a)) & (d.index <= pd.Timestamp(b) + pd.Timedelta(days=1))]
    days = x.index.normalize(); nd = pd.DatetimeIndex(np.unique(days))
    nights = 0.0
    for k in range(1, len(nd)):
        nights += 3.0 if nd[k - 1].dayofweek == 2 else 1.0
    g = x.close.iloc[-1] - (x.open.iloc[0] + 0.30 + 0.10) - 0.10
    return round((g - nights * SWAP_L) / len(nd), 2), round(g / len(nd), 2)
