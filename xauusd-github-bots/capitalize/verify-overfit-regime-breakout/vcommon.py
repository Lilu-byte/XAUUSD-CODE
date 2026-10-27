"""Adversarial overfitting check of the 'regime-breakout' candidate (DON 120/60, 2.5*ATR48 stop, D1 MOM6 gate, both dirs).
Own signal construction (parameterised); engine = ../../code/gbt.py simulate (not edited).
OANDA H1 2006-2019 from QuantConnect/Lean, read only as data from /tmp/claude-0/oanda-verify-overfit-rb/csv/."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
from gbt import load, htf, sma, atr, simulate, daily, SWAP_L  # noqa: F401

P = '/mnt/project-files/'
TRAIN = ('2016-07-29', '2021-12-31')
TEST = ('2022-01-01', '2026-10-31')
COMMON = ('2025-05-05', '2026-10-31')
OOS_OANDA = ('2006-06-01', '2016-07-28')
OANDA_F = '/tmp/claude-0/oanda-verify-overfit-rb/csv/xauusd.csv'

PICK = dict(ent=120, ex=60, atr_n=48, k=2.5, mom=126, gate=True, long_only=False)


def oanda():
    x = pd.read_csv(OANDA_F, header=None, names=['t', 'bo', 'bh', 'bl', 'bc', 'v', 'ao', 'ah', 'al', 'ac', 'v2'])
    ts = (pd.to_datetime(x.t, format='%Y%m%d %H:%M').dt.tz_localize('UTC').dt.tz_convert('America/New_York')
          .dt.tz_localize(None) + pd.Timedelta(hours=7))           # MT5 server time = New York + 7h
    o = pd.DataFrame({'open': x.bo.values, 'high': x.bh.values, 'low': x.bl.values, 'close': x.bc.values,
                      'spread': (x.ac - x.bc).values, 'vol': 0.0}, index=pd.DatetimeIndex(ts)).sort_index()
    return o[~o.index.duplicated()]


def mom_regime(mom):
    D = load('D1'); c = D.close
    return np.sign(c / c.shift(mom) - 1).fillna(0).values


def build(d, ent=120, ex=60, atr_n=48, k=2.5, mom=126, gate=True, long_only=False, short_only=False):
    a = atr(d, atr_n)
    hh = d.high.shift().rolling(ent).max(); ll = d.low.shift().rolling(ent).min()
    xh = d.high.shift().rolling(ex).max(); xl = d.low.shift().rolling(ex).min()
    sig = np.where(d.close > hh, 1.0, np.where(d.close < ll, -1.0, 0.0))
    if gate:
        g = np.nan_to_num(htf(d, 'D1', mom_regime(mom)))
        sig = np.where(((sig > 0) & (g > 0)) | ((sig < 0) & (g < 0)), sig, 0.0)
    if long_only: sig = np.where(sig > 0, sig, 0.0)
    if short_only: sig = np.where(sig < 0, sig, 0.0)
    kw = dict(sl=(k * a).values, exit_long=(d.close < xl).values, exit_short=(d.close > xh).values)
    return sig, kw


def run(d, **p):
    sig, kw = build(d, **p)
    cost = p.get('_cost', None)
    return simulate(d, sig, **kw)


def win(p, a, b):
    return p[(p.index >= pd.Timestamp(a)) & (p.index <= pd.Timestamp(b))]


def summ(p):
    eq = p.cumsum(); m = p.groupby(p.index.to_period('M')).sum()
    return dict(per_day=round(p.mean(), 2), total=round(p.sum(), 0), max_dd=round((eq - eq.cummax()).min(), 0),
                losing_months=f'{(m < 0).sum()}/{len(m)}', days=len(p))


def hold_daily(d):
    """Daily P&L of holding 0.01 lot long (close-to-close), minus long swap per night (triple Wed)."""
    c = d.close.groupby(d.index.normalize()).last()
    pnl = c.diff().fillna(0.0)
    sw = np.r_[0.0, np.where(c.index[:-1].dayofweek == 2, 3.0, 1.0)] * SWAP_L
    return pnl - sw


def pair_daily():
    m5 = load('M5'); days = pd.DatetimeIndex(np.unique(m5.index.normalize()))
    a = pd.read_csv(P + 'xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
    b = pd.read_csv(P + 'xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
    pa = a.groupby(a.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0.0)
    pb = b.groupby(b.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0)
    return days, pa + pb, a, b
