"""Scoring as the EA trades: ea_sim._sim_next (entry at the NEXT bar's open), with ea_replica.run_ea's entry
filters (bar i+1 must follow bar i directly; recorded spread of bar i+1 <= $0.50). Adds: fill / spread model /
cooldown / extra cost per trade / 1-bar latency. Nothing shared is modified."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from mlib import Harness, FILL, SPLIT, spread_series, random_like, load_m1
from ea_sim import _sim_next

MAX_SPREAD = 0.50


class EASim:
    def __init__(self, m=None):
        self.H = Harness(m) if m is not None else Harness()
        m = self.H.m1
        gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
        raw = spread_series(m, 'bar')
        nxt = np.r_[raw[1:], 99.0]
        bar_s = int(np.median(np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64)))
        self.ok = (gap == bar_s) & (nxt <= MAX_SPREAD)
        self.train = m.index < SPLIT
        self.dtrain = self.H.dates < SPLIT

    def run(self, sig, tp=1000.0, sl=10.0, timeout=5, max_open=1, cooldown=0, fill='FAIR', spread='base',
            extra=0.0, latency=0):
        H = self.H
        s = np.sign(np.nan_to_num(np.asarray(sig, float))).astype(np.int64)
        if latency:
            s = np.r_[np.zeros(latency, np.int64), s[:-latency]]
            # the delayed signal is acted on at the close of bar i+latency; that bar must follow directly too
            gap_ok = np.r_[np.zeros(latency, bool), np.ones(len(s) - latency, bool)]
            idx = H.m1.index.values
            for j in range(1, latency + 1):
                d = np.r_[np.zeros(j, 'timedelta64[ns]'), idx[j:] - idx[:-j]]
                gap_ok &= (d.astype('timedelta64[s]').astype(np.int64) == 60 * j) | (np.arange(len(s)) < j)
            s = np.where(gap_ok, s, 0)
        s = np.where(self.ok, s, 0)
        spr = H._spr[spread] + extra
        dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, spr, H.tod, H.day, H.last, s,
                                             float(tp), float(sl), int(timeout), int(max_open), FILL[fill],
                                             0.0, 0.0, int(cooldown))
        days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=H.dates)
        trades = pd.DataFrame({'entry': H.m1.index[ti], 'dir': tdr, 'pnl': tpn,
                               'bars': np.where(to >= 0, to - ti, -1)})
        return days, trades


def stats(days, trades, period):
    if period == 'train':
        days = days[days.index < SPLIT]; trades = trades[trades.entry < SPLIT]
    elif period == 'test':
        days = days[days.index >= SPLIT]; trades = trades[trades.entry >= SPLIT]
    elif period == 'h1':
        days = days[days.index < pd.Timestamp('2026-08-01')]; trades = trades[trades.entry < pd.Timestamp('2026-08-01')]
    elif period == 'h2':
        lo, hi = pd.Timestamp('2026-08-01'), SPLIT
        days = days[(days.index >= lo) & (days.index < hi)]; trades = trades[(trades.entry >= lo) & (trades.entry < hi)]
    p = days.pnl; eq = p.cumsum(); nd = max(len(p), 1); nt = len(trades)
    return dict(per_day=p.mean(), trades_day=nt / nd, win=(trades.pnl > 0).mean() if nt else np.nan,
                per_trade=trades.pnl.mean() if nt else np.nan, days_ge5=(p >= 4.99).mean(),
                losing_days=(p < 0).mean(), worst_day=p.min(), worst_trade=trades.pnl.min() if nt else np.nan,
                max_dd=(eq - eq.cummax()).min(), long_share=(trades.dir == 1).mean() if nt else np.nan,
                total=p.sum(), days=len(p), n=nt)
