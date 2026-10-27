"""Independent long/flat D1 simulator for the adversarial check of long-core (written from scratch;
does NOT import long-core/common.py). Conventions copied from gbt.py: decision on closed bar i,
fill at bar i+1 open; buy = open + $0.30 spread + $0.10 slip, sell = open - $0.10;
swap per night held (bar i-1 -> bar i), triple when bar i-1 is a Wednesday.
Swap modes: 'fixed' = $0.126/night; a number = that $ per night; 'scaled' = rate_pct %/yr of the prior close (365-day basis)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd
import gbt

OUT = '/mnt/project-files/xauusd-github-bots/capitalize/verify-overfit-long-core/'
TRAIN_A = ('2005-04-01', '2015-12-31')
TRAIN_B = ('2016-07-29', '2021-12-31')
TEST = ('2022-01-01', '2026-10-31')
COMMON = ('2025-05-01', '2026-10-31')


def mtm(on, d, swap='fixed', rate_pct=None, spread=0.30, slip=0.10, fill=None):
    """on[i]: desired state after bar i closes. fill: optional array of entry/exit prices to use instead
    of bar opens (e.g. 02:00 server price), same index as d (price at which bar i's action fills).
    Returns daily pnl Series, held Series (position during bar i), trade DataFrame."""
    on = np.asarray(on, bool)
    o = d.open.values if fill is None else np.asarray(fill, float)
    c = d.close.values; dow = d.index.dayofweek.values; n = len(d)
    pnl = np.zeros(n); held = np.zeros(n, bool); tr = []
    pos = False; ent = 0.0; ei = 0; sw = 0.0
    for i in range(1, n):
        if pos:
            k = 3.0 if dow[i - 1] == 2 else 1.0
            s = 0.126 if swap == 'fixed' else (float(swap) if not isinstance(swap, str) else c[i - 1] * rate_pct / 100.0 / 365.0)
            pnl[i] -= k * s; sw += k * s
            if not on[i - 1]:
                px = o[i] - slip
                pnl[i] += px - c[i - 1]
                tr.append((d.index[ei], ent, d.index[i], px, sw, False)); pos = False
            else:
                pnl[i] += c[i] - c[i - 1]; held[i] = True
        elif on[i - 1]:
            ent = o[i] + spread + slip; ei = i; pos = True; sw = 0.0
            pnl[i] += c[i] - ent; held[i] = True
    if pos:
        tr.append((d.index[ei], ent, d.index[-1], c[-1], sw, True))
    t = pd.DataFrame(tr, columns=['entry_time', 'entry', 'exit_time', 'exit', 'swap', 'open_at_end'])
    t['pnl'] = t.exit - t.entry - t.swap
    return pd.Series(pnl, d.index), pd.Series(held, d.index), t


def win(s, w):
    return s.loc[w[0]:w[1]]


def m(p, price=None):
    eq = p.cumsum(); dd = (eq - eq.cummax()).min()
    mo = p.groupby(p.index.to_period('M')).sum()
    r = dict(per_day=round(p.mean(), 2), max_dd=round(dd, 0), losing_m=f'{(mo < 0).sum()}/{len(mo)}', days=len(p))
    if price is not None:
        ret = p / price.shift().reindex(p.index)
        r['ret_yr_pct'] = round(ret.mean() * 252 * 100, 1)
        r['sharpe'] = round(ret.mean() / ret.std() * np.sqrt(252), 2) if ret.std() > 0 else np.nan
    return r


def golden(c, fast=50, slow=200, kind='sma'):
    if kind == 'sma':
        f, s = c.rolling(fast).mean(), c.rolling(slow).mean()
    else:
        f, s = c.ewm(span=fast, adjust=False).mean(), c.ewm(span=slow, adjust=False).mean()
        s[:slow] = np.nan
    return ((f > s) & s.notna()).values


def pair_daily():
    a = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
    b = pd.read_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
    days = pd.DatetimeIndex(np.unique(gbt.load('M5').index.normalize()))
    pa = a.groupby(a.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0.0)
    pb = b.groupby(b.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0)
    return pa + pb, a, b, days
