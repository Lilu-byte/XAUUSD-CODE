"""Snap-back history family: shared loader, pre-specified signals and the next-bar-open scorer for M5/M15.

Pre-specified rule (from the M1 finding, no search beyond the grid in the task):
  AR_i   = mean(high - low) over the L bars ending at bar i-1   (L = 48 on M5, 32 on M15)
  move_i = close[i] - close[i-n], n in {1, 2}; the bars i-n..i must be consecutive (no session break inside)
  signal = -sign(move_i) when |move_i| > k * AR_i, k in {2.5, 3, 4}           (fade the move)
  VWAP gate (optional): session VWAP_i = cumsum(tp * tick_volume) / cumsum(tick_volume) from the day's first bar,
                        tp = (high + low + close) / 3; keep up-moves only if close_i > VWAP_i (then short),
                        down-moves only if close_i < VWAP_i (then long).
Entry: next bar's open (long at open + spread, short at open), only if bar i+1 follows bar i directly and the
recorded spread of bar i+1 is <= $0.50 (EA rules from ea_replica.run_ea). Exit: close of bar i+N (N full bars),
disaster stop sl, everything flat at the last bar of the session / 22:58; no entries on signal bars before 01:05
or after 22:29 (mlib v2 constants, applied by ea_sim._sim_next).
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from mlib import Harness, FILL, random_like, load_m1
from ea_sim import _sim_next

FILES = {'M5': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv',
         'M15': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv'}
BARMIN = {'M5': 5, 'M15': 15}
AR_LEN = {'M5': 48, 'M15': 32}
MAX_SPREAD = 0.50
COMMISSION = 0.07


def load_tf(tf):
    d = pd.read_csv(FILES[tf])
    d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    d = d[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].astype(float)
    d = d[d.index.dayofweek < 5]
    sp = d.spread.copy()
    nz = sp > 0
    key_m = d.index.to_period('M').astype(str) + '_' + d.index.hour.astype(str)
    med_m = sp[nz].groupby(key_m[nz]).median()
    med_h = sp[nz].groupby(d.index.hour[nz]).median()
    zero = ~nz
    fill = pd.Series(key_m[zero], index=d.index[zero]).map(med_m)
    fill = fill.fillna(pd.Series(d.index[zero].hour, index=d.index[zero]).map(med_h))
    sp[zero] = fill.values                              # zero recorded spreads -> same month/hour median
    d['spread_usd'] = sp * 0.01
    d['zero_spread'] = zero
    d['tod'] = d.index.hour * 60 + d.index.minute
    nxt = d.index.to_series().shift(-1)
    d['last_of_session'] = ((nxt - d.index.to_series()) > pd.Timedelta(minutes=30)) | nxt.isna()
    return d


def features(d, tf):
    """Per-bar quantities the signals need, computed causally (bar i uses bars <= i only)."""
    L = AR_LEN[tf]; bm = BARMIN[tf]
    rng = d.high - d.low
    ar = rng.rolling(L).mean().shift(1)
    day = d.index.normalize()
    tp = (d.high + d.low + d.close) / 3
    vw = (tp * d.tick_volume).groupby(day).cumsum() / d.tick_volume.groupby(day).cumsum()
    t = d.index.to_series()
    step = (t.diff() == pd.Timedelta(minutes=bm))          # bar i follows bar i-1 directly
    f = pd.DataFrame({'ar': ar, 'vwap': vw}, index=d.index)
    for n in (1, 2):
        f[f'mv{n}'] = d.close - d.close.shift(n)
        f[f'ok{n}'] = step.rolling(n).sum() == n            # bars i-n..i consecutive
    return f


def signal(d, f, n, k, gate):
    mv = f[f'mv{n}']; ok = f[f'ok{n}'] & f.ar.notna()
    big = ok & (mv.abs() > k * f.ar)
    s = np.where(big, -np.sign(mv), 0.0)
    if gate:
        up = (mv > 0) & (d.close > f.vwap); dn = (mv < 0) & (d.close < f.vwap)
        s = np.where(big & (up | dn), s, 0.0)
    return s.astype(float)


class Scorer:
    """Wraps mlib.Harness (same arrays) and runs ea_sim._sim_next with the EA entry rules."""

    def __init__(self, d, tf, ar=None):
        self.d = d; self.tf = tf
        self.ar = np.full(len(d), np.nan) if ar is None else np.asarray(ar, float)
        self.H = Harness(m1=d)
        bm = BARMIN[tf] * 60
        gap = np.r_[np.diff(d.index.values).astype('timedelta64[s]').astype(np.int64), 10**6]
        raw = d.spread_usd.values
        nxt = np.r_[raw[1:], 99.0]
        self.entry_ok = (gap == bm) & (nxt <= MAX_SPREAD)

    def prep(self, s, latency=0):
        s = np.sign(np.nan_to_num(np.asarray(s, float)))
        if latency:
            s = np.r_[np.zeros(latency), s[:-latency]]
        return np.where(self.entry_ok, s, 0).astype(np.int64)

    def run(self, s, N, sl, max_open, spread='base', fill='FAIR', tp=1000.0, latency=0):
        H = self.H
        s = self.prep(s, latency)
        dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, H._spr[spread], H.tod, H.day, H.last, s,
                                             float(tp), float(sl), int(N), int(max_open), FILL[fill], 0.0, 0.0, 0)
        days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=H.dates)
        T = pd.DataFrame({'entry': self.d.index[ti], 'dir': tdr, 'pnl': tpn, 'bars': np.where(to >= 0, to - ti, -1),
                          'ar': self.ar[ti]})
        return days, T


def stats(days, T, lo=None, hi=None, extra=0.0):
    """Per-day statistics over trading days in [lo, hi). extra = cost added per trade (e.g. commission)."""
    sel = np.ones(len(days), bool)
    tsel = np.ones(len(T), bool)
    if lo is not None:
        sel &= days.index >= pd.Timestamp(lo); tsel &= T.entry >= pd.Timestamp(lo)
    if hi is not None:
        sel &= days.index < pd.Timestamp(hi); tsel &= T.entry < pd.Timestamp(hi)
    p = days.pnl[sel] - extra * days.trades[sel]
    t = T.pnl[tsel] - extra
    nd = max(len(p), 1); eq = p.cumsum()
    return dict(per_day=p.mean() if len(p) else np.nan, trades_day=len(t) / nd,
                win=(t > 0).mean() if len(t) else np.nan, per_trade=t.mean() if len(t) else np.nan,
                days_ge5=(p >= 4.99).mean() if len(p) else np.nan, losing_days=(p < 0).mean() if len(p) else np.nan,
                worst_day=p.min() if len(p) else np.nan, worst_trade=t.min() if len(t) else np.nan,
                max_dd=(eq - eq.cummax()).min() if len(p) else np.nan, total=p.sum(), days=len(p), trades=len(t),
                long_share=(T.dir[tsel] == 1).mean() if len(t) else np.nan)
