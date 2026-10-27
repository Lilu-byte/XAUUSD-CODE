"""Verifier library (history / tail-risk lens) for the snapback-m1-fade pick P1_snap_time3.
Independent re-implementation of the P1 signal and EA entry filter; trades are simulated with the audited
next-bar-open simulator ea/ea_sim._sim_next (imported read-only, nothing in code/ or ea/ is modified).
Run with NUMBA_CACHE_DIR pointing at a scratch dir and PYTHONDONTWRITEBYTECODE=1 so nothing is written elsewhere."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from mlib import load_m1, SPLIT, FILL, random_like
from ea_sim import _sim_next

OUT = '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/'
HALF = pd.Timestamp('2026-08-01')
FILES = {'M5': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv',
         'M15': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv'}
SECS = {'M1': 60, 'M5': 300, 'M15': 900}
M1START = pd.Timestamp('2026-06-26')


def load_tf(tf):
    """M5 / M15 bars with the columns the simulator needs (spread_usd from the recorded bar spread, zeros -> hour median)."""
    if tf == 'M1':
        return load_m1()
    d = pd.read_csv(FILES[tf]); d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    d = d[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].astype(float)
    d = d[d.index.dayofweek < 5]
    sp = d.spread.copy(); pos = sp > 0
    med = sp[pos].groupby(sp[pos].index.hour).median()
    sp[~pos] = d.index[~pos].hour.map(med).values
    d['spread_usd'] = sp * 0.01
    d['tod'] = d.index.hour * 60 + d.index.minute
    nxt = d.index.to_series().shift(-1)
    d['last_of_session'] = ((nxt - d.index.to_series()) > pd.Timedelta(minutes=30)) | nxt.isna()
    return d


class Arr:
    def __init__(self, m):
        self.m = m
        dates = m.index.normalize()
        u, inv = np.unique(dates.values, return_inverse=True)
        self.dates = pd.DatetimeIndex(u); self.day = inv.astype(np.int64)
        self.o, self.h, self.l, self.c = (m[k].values.astype(np.float64) for k in ('open', 'high', 'low', 'close'))
        self.tod = m.tod.values.astype(np.int64)
        self.last = m.last_of_session.values.astype(np.bool_)
        self.bar_spr = m.spread_usd.values.astype(np.float64)


def ea_filter(m, s, secs=60, max_spread=0.50, use_spread=True):
    """EA entry rule: bar i+1 must open exactly `secs` after bar i, and (M1) its recorded spread <= $0.50."""
    s = np.sign(np.nan_to_num(np.asarray(s, float)))
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
    ok = gap == secs
    if use_spread:
        nxt = np.r_[m.spread_usd.values[1:], 99.0]
        ok &= nxt <= max_spread + 1e-9
    return np.where(ok, s, 0).astype(np.int64)


def p1_signal(m, th=7.0, k=3):
    """P1: r_k = Close[i] - Close[i-k]; |r_k| > th dollars -> trade against the move."""
    r = (m.close - m.close.shift(k)).values
    return np.where(np.abs(r) > th, -np.sign(r), 0.0)


def run(A, sig, tp=1000.0, sl=10.0, timeout=3, max_open=2, spr=None, fill='FAIR', secs=60, use_spread=True,
        filt=True, latency=0, cooldown=0):
    s = np.asarray(sig, float)
    if latency:
        s = np.r_[np.zeros(latency), s[:-latency]]
    s = ea_filter(A.m, s, secs, use_spread=use_spread) if filt else np.sign(np.nan_to_num(s)).astype(np.int64)
    if spr is None:
        spr = A.bar_spr + 0.05
    spr = np.asarray(spr, np.float64)
    if spr.ndim == 0:
        spr = np.full(len(A.c), float(spr))
    dp, dt, ti, to, pn, dr = _sim_next(A.o, A.h, A.l, A.c, spr, A.tod, A.day, A.last, s, float(tp), float(sl),
                                       int(timeout), int(max_open), FILL[fill], 0.0, 0.0, int(cooldown))
    days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=A.dates)
    tr = pd.DataFrame({'entry': A.m.index[ti], 'ei': ti, 'xi': to, 'dir': dr, 'pnl': pn,
                       'bars': np.where(to >= 0, to - ti, -1)})
    return days, tr


def summ(days, tr, a=None, b=None, fee=0.0):
    d = days.copy(); t = tr
    if fee:
        cnt = t.groupby(t.entry.dt.normalize()).size().reindex(d.index, fill_value=0)
        d['pnl'] = d.pnl - fee * cnt.values; t = t.assign(pnl=t.pnl - fee)
    sel = np.ones(len(d), bool)
    if a is not None: sel &= d.index >= a
    if b is not None: sel &= d.index < b
    d = d[sel]; t = t[t.entry.dt.normalize().isin(d.index)]
    p = d.pnl; eq = p.cumsum(); nd = max(len(p), 1)
    return dict(per_day=p.mean(), trades_day=len(t) / nd, win=(t.pnl > 0).mean() if len(t) else np.nan,
                per_trade=t.pnl.mean() if len(t) else np.nan, days_ge5=(p >= 4.99).mean(), losing_days=(p < 0).mean(),
                worst_day=p.min(), worst_trade=t.pnl.min() if len(t) else np.nan, max_dd=(eq - eq.cummax()).min(),
                total=p.sum(), days=len(p), long_share=(t.dir == 1).mean() if len(t) else np.nan, n=len(t))


def line(name, r):
    return (f'{name:44s} {r["per_day"]:+7.2f}/day {r["trades_day"]:5.1f} tr/d win {r["win"]:.2f} {r["per_trade"]:+.3f}/tr '
            f'losing {r["losing_days"]:.2f} worst day {r["worst_day"]:+6.1f} maxDD {r["max_dd"]:+7.1f} long {r["long_share"]:.2f}')
