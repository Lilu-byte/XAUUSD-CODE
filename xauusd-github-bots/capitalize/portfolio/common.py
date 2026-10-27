"""Portfolio view: shared helpers.
Third-bot candidates come unchanged from ../../code/bots.py (maxi, donchian, maker_tung).
Portfolio rules are applied as masks on the bot's signal / extra exits, then run through gbt.simulate.
Periods: train 2016-07..2021-12 (rules chosen here only), test 2022-01..2026-10 (scored once),
common window 2025-05-05..2026-10-09 (the pair's replay window)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd
from gbt import load, htf, ema, sma, atr, simulate, daily, stats, by_year, coinflip
import bots

TRAIN = (pd.Timestamp('2016-07-29'), pd.Timestamp('2022-01-01'))
TEST = (pd.Timestamp('2022-01-01'), pd.Timestamp('2026-11-01'))
COMMON = pd.Timestamp('2025-05-05')
OUT = '/mnt/project-files/xauusd-github-bots/capitalize/portfolio/'
GAA_CSV = '/mnt/project-files/xauusd-mt5/expected_trades_M5.csv'
ASIA_CSV = '/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv'


# ---------------- the pair ----------------
def pair_trades():
    g = pd.read_csv(GAA_CSV, parse_dates=['entry_time', 'exit_time'])
    a = pd.read_csv(ASIA_CSV, parse_dates=['entry_time', 'exit_time'])
    return g, a


def m5_days():
    return pd.DatetimeIndex(np.unique(load('M5').index.normalize()))


def pair_daily():
    g, a = pair_trades(); days = m5_days()
    pg = g.groupby(g.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0.0)
    pa = a.groupby(a.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0)
    return pg, pa


def gaa_actual_on(d):
    """1.0 where the real GoldAllAgree replay holds its long at the CLOSE of each bar of d
    (bar close = index + bar length); NaN before the replay starts."""
    g, _ = pair_trades()
    step = d.index[1:] - d.index[:-1]
    bar = pd.Timedelta(hours=1) if (pd.Series(step).mode()[0] == pd.Timedelta(hours=1)) else pd.Series(step).mode()[0]
    tclose = d.index + bar
    st = np.zeros(len(d))
    e = g.entry_time.values; x = g.exit_time.values
    tc = tclose.values
    # position open at time t if entry <= t < exit
    ie = np.searchsorted(e, tc, side='right') - 1        # last entry at or before t
    ok = ie >= 0
    st[ok] = (x[ie[ok]] > tc[ok]).astype(float)
    st[tclose < g.entry_time.iloc[0]] = np.nan
    return st


def gaa_proxy(d):
    """GoldAllAgree proxy for older years: EMA20>EMA80 on H1 and on closed H4 bars (decided at the H1 close)."""
    c = d.close
    h1 = (ema(c, 20) > ema(c, 80)).values
    h4 = load('H4'); up4 = (ema(h4.close, 20) > ema(h4.close, 80)).astype(float).values
    u4 = htf(d, 'H4', up4) > 0.5
    return (h1 & u4).astype(float)


def gaa_state(d, prefer_actual=True):
    """Actual replay state where it exists (from 2025-05-05), H1+H4 proxy before."""
    p = gaa_proxy(d)
    if not prefer_actual:
        return p
    a = gaa_actual_on(d)
    return np.where(np.isnan(a), p, a)


# ---------------- third-bot candidates ----------------
def candidate(name):
    if name == 'maxi':
        return bots.maxi()
    if name == 'donchian':
        return bots.donchian()
    if name == 'maker_tung':
        return bots.maker_tung()
    raise KeyError(name)


def d1_regime(d, kind):
    """Slow regime flags mapped onto H1 bars from CLOSED D1 bars. Returns (long_ok, short_ok)."""
    D = load('D1'); c = D.close
    if kind == 'none':
        return np.ones(len(d), bool), np.ones(len(d), bool)
    if kind == 'sma200':
        up = (c > sma(c, 200))
    elif kind == 'sma50_200':
        up = (sma(c, 50) > sma(c, 200))
    elif kind == 'mom252':
        up = c > c.shift(252)
    elif kind == 'mom126':
        up = c > c.shift(126)
    else:
        raise KeyError(kind)
    f = htf(d, 'D1', up.astype(float).values)
    return f > 0.5, f < 0.5


def window(t, d, a, b):
    dd = d[(d.index >= a) & (d.index < b)]
    tt = t[(t.exit_time >= a) & (t.exit_time < b)]
    return tt, dd


def per_day(t, d, a, b):
    tt, dd = window(t, d, a, b)
    return daily(tt, dd).mean()


def maxdd(p):
    eq = p.cumsum(); return float((eq - eq.cummax()).min())


def losing_months(p):
    m = p.groupby(p.index.to_period('M')).sum()
    return int((m < 0).sum()), len(m), m


def hold_gold(d, a, b):
    """0.01 lot bought at the first open of the window, sold at the last close, minus swap (engine rules)."""
    dd = d[(d.index >= a) & (d.index < b)]
    sig = np.zeros(len(dd)); sig[0] = 1
    # enter at bar 1 open, exit at the final bar's open via exit flag on the bar before
    xl = np.zeros(len(dd), bool); xl[-2] = True
    t = simulate(dd, np.r_[1.0, np.zeros(len(dd) - 1)], exit_long=xl)
    return daily(t, dd).mean(), t
