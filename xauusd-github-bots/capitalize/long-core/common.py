"""Long-bias core position on XAUUSD D1: shared helpers (approach C, folder long-core).

One 0.01 lot ($1 per $1 gold move), long or flat, decided on CLOSED D1 bars (server time),
filled at the NEXT D1 bar's open: buy at open + spread $0.30 + slippage $0.10, sell at open - $0.10
(same convention as gbt.py). Swap per night held, triple on Wednesday night (gbt convention).
Swap modes:
  'fixed'  : $0.126 per night (today's broker swap; gbt convention, used for all $ results)
  'scaled' : $0.126 * close / 4100 (same % of price as today, ~1.1%/yr; used for 2004-2015 history
             where a fixed $0.126 on $400 gold would be an unrealistic 11%/yr)
Results are mark-to-market (MTM) by day, which is what the account equity shows; the
"realized" view books each trade's P&L on its exit date (project convention for trade lists).
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd
import gbt

SPREAD, SLIP, SWAP = gbt.SPREAD, gbt.SLIP, gbt.SWAP_L
OUT = '/mnt/project-files/xauusd-github-bots/capitalize/long-core/'
D1 = gbt.load('D1')

TRAIN_A = ('2005-04-01', '2015-12-31')   # D1 history (first 200-day average exists ~Apr 2005)
TRAIN_B = ('2016-07-29', '2021-12-31')   # project training window
TEST = ('2022-01-01', '2026-10-31')
COMMON = ('2025-05-01', '2026-10-31')


def run(on, d=D1, swap='fixed', start=None):
    """on: boolean array aligned to d, the desired state decided at bar i's close (acts from bar i+1 open).
    Returns (trades DataFrame, daily MTM pnl Series indexed by d's dates, position held during each bar)."""
    on = np.asarray(on, bool)
    o, c = d.open.values, d.close.values
    dow = d.index.dayofweek.values
    n = len(d)
    i0 = 0 if start is None else int(np.searchsorted(d.index.values, np.datetime64(pd.Timestamp(start))))
    pnl = np.zeros(n); held = np.zeros(n, bool)
    trades = []
    pos = 0; ent = 0.0; ei = 0; sw_acc = 0.0
    for i in range(max(i0, 1), n):
        want = on[i - 1]
        if pos == 1:
            # swap for the night between bar i-1 and bar i
            nights = 3.0 if dow[i - 1] == 2 else 1.0
            s = SWAP if swap == 'fixed' else SWAP * c[i - 1] / 4100.0
            pnl[i] -= nights * s; sw_acc += nights * s
            if not want:   # exit at this bar's open
                px = o[i] - SLIP
                pnl[i] += px - c[i - 1]
                trades.append((d.index[ei], ent, d.index[i], px, px - ent, sw_acc))
                pos = 0
            else:
                pnl[i] += c[i] - c[i - 1]; held[i] = True
        elif want:
            ent = o[i] + SPREAD + SLIP; ei = i; pos = 1; sw_acc = 0.0
            pnl[i] += c[i] - ent; held[i] = True
    if pos == 1:   # still open at the end: mark at last close (open trade, flagged)
        trades.append((d.index[ei], ent, d.index[n - 1], c[n - 1], c[n - 1] - ent, sw_acc))
    t = pd.DataFrame(trades, columns=['entry_time', 'entry', 'exit_time', 'exit', 'gross', 'swap'])
    t['pnl'] = t.gross - t.swap
    t['open_at_end'] = False
    if pos == 1:
        t.loc[t.index[-1], 'open_at_end'] = True
    return t, pd.Series(pnl, index=d.index), pd.Series(held, index=d.index)


def hold(d=D1, swap='fixed', start=None):
    return run(np.ones(len(d), bool), d, swap, start)


def window(s, w):
    return s.loc[w[0]:w[1]]


def metr(p, d=D1, pct=False):
    """p: daily MTM pnl ($). Returns $/day, maxDD ($, MTM), Sharpe, % metrics on a 1-oz basis."""
    eq = p.cumsum(); dd = (eq - eq.cummax()).min()
    r = p / d.close.shift().reindex(p.index)   # daily return of a 1-oz position
    req = r.cumsum(); rdd = (req - req.cummax()).min()
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan
    m = p.groupby(p.index.to_period('M')).sum()
    return dict(per_day=round(p.mean(), 2), max_dd=round(dd, 0), ret_yr=round(r.mean() * 252 * 100, 1),
                dd_pct=round(rdd * 100, 1), sharpe=round(sh, 2), mar=round(r.mean() * 252 / -rdd, 2) if rdd < 0 else np.nan,
                losing_months=f'{(m < 0).sum()}/{len(m)}', days=len(p))


def tstats(t, w):
    x = t[(t.exit_time >= w[0]) & (t.entry_time <= w[1])]
    return dict(trades=len(x), win=round((x.pnl > 0).mean() * 100, 1) if len(x) else np.nan)


def pair_daily():
    """Pair (GoldAllAgree + GoldAsiaBreak) realized P&L by exit date on M5 trading days."""
    a = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
    b = pd.read_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
    days = pd.DatetimeIndex(np.unique(gbt.load('M5').index.normalize()))
    pa = a.groupby(a.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0.0)
    pb = b.groupby(b.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0)
    return pa + pb, a, b, days


def sma(n): return D1.close.rolling(n).mean()


def friday_only(on_daily, d=D1):
    """Re-evaluate state only at the last bar of each week; hold the state until next week's check."""
    s = pd.Series(np.where(np.isnan(on_daily.astype(float)), np.nan, on_daily.astype(float)), index=d.index)
    wk = d.index.to_period('W-SUN')
    last = pd.Series(wk, index=d.index) != pd.Series(wk, index=d.index).shift(-1)
    last.iloc[-1] = d.index[-1].dayofweek == 4   # last bar counts only if it is a Friday
    v = s.where(last.values)
    return v.ffill().fillna(0).values.astype(bool)
