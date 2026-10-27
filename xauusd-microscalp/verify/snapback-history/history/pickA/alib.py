"""Verifier library for pick A (independent re-implementation; reads shared code only).

Pick A on M15 (colleague's rule):
  AR_i  = mean(high - low) over bars i-32 .. i-1
  move  = close[i] - close[i-2], bars i-2, i-1, i consecutive (15 min apart)
  VWAP_i = cumsum((H+L+C)/3 * tick_volume) / cumsum(tick_volume) over the server date, bars <= i
  SELL if move > 4*AR_i and close_i > VWAP_i ; BUY if move < -4*AR_i and close_i < VWAP_i
  entry at open of bar i+1 if it starts 15 min after bar i and its recorded spread <= 50 points;
  signal-bar tod 01:05..22:29; no TP; disaster stop $25; exit at close of bar i+4; max 3 open.

Generalised for a bar size B (minutes) with M15-equivalent windows (w = 15/B bars):
  R_j = max(high[j-w+1..j]) - min(low[j-w+1..j])   (rolling 15-minute range; = high-low when w = 1)
  AR_i = mean of R_j over j = i-32w .. i-1
  move = close[i] - close[i-2w], bars i-2w..i consecutive; hold 4w bars.
"""
import sys, numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from mlib import Harness, FILL
from ea_sim import _sim_next

F = {'M1': '/mnt/project-files/xauusd-microscalp/data/XAUUSD_M1.csv',
     'M5': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv',
     'M15': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv',
     'H1': '/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv'}
END_TOD = 22 * 60 + 58; FIRST = 65; LAST = 22 * 60 + 29
MAXSPR = 0.50; COMM = 0.07


def read(tf):
    d = pd.read_csv(F[tf])
    d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    d = d[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].astype(float)
    return d[d.index.dayofweek < 5]


def finish(d, bar_min=None):
    """spread_usd (zero spreads -> same month+hour median, else hour median), tod, last_of_session
    (next bar more than max(30 min, 1.5 bars) away; the 1.5-bar part only matters for H1)."""
    d = d.copy()
    sp = d.spread.copy(); nz = sp > 0
    mon = d.index.year * 100 + d.index.month; hr = d.index.hour
    mm = sp[nz].groupby([mon[nz], hr[nz]]).median()
    mh = sp[nz].groupby(hr[nz]).median()
    z = np.where(~nz)[0]
    vals = []
    for j in z:
        key = (mon[j], hr[j])
        vals.append(mm[key] if key in mm.index else mh[hr[j]])
    sp.iloc[z] = vals
    d['spread_usd'] = sp.values * 0.01
    d['tod'] = d.index.hour * 60 + d.index.minute
    t = d.index.to_series(); nxt = t.shift(-1)
    gapmin = 30 if bar_min is None else max(30, 1.5 * bar_min)
    d['last_of_session'] = ((nxt - t) > pd.Timedelta(minutes=gapmin)) | nxt.isna()
    return d


def resample_phase(d, minutes, offset):
    """Clock bars of `minutes` built from finer bars d, shifted by `offset` minutes (label = bar open).
    spread = lowest recorded spread inside the bar (as MT5 records it)."""
    g = d.resample(f'{minutes}min', label='left', closed='left', offset=f'{offset}min')
    out = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(), 'close': g.close.last(),
                        'tick_volume': g.tick_volume.sum(), 'spread': g.spread.min(), 'nsub': g.close.count()})
    return out[out.nsub > 0].drop(columns='nsub')


def features(d, B, w=None, L=32, n=2):
    """Pick-A quantities on bars of B minutes; w = bars per 15 minutes (default 15/B)."""
    if w is None: w = max(int(round(15 / B)), 1)
    h = d.high.rolling(w).max(); l = d.low.rolling(w).min()
    R = (h - l) if w > 1 else (d.high - d.low)
    ar = R.rolling(L * w).mean().shift(1)
    nn = n * w
    t = d.index.values.astype('datetime64[m]').astype(np.int64)
    span = np.full(len(d), -1, np.int64); span[nn:] = t[nn:] - t[:-nn]
    cont = span == nn * B                                   # bars i-nn..i consecutive (no gap)
    mv = d.close - d.close.shift(nn)
    day = d.index.normalize()
    tp = (d.high + d.low + d.close) / 3
    vw = (tp * d.tick_volume).groupby(day).cumsum() / d.tick_volume.groupby(day).cumsum()
    return pd.DataFrame({'ar': ar, 'mv': mv, 'cont': cont, 'vwap': vw}, index=d.index)


def signal(d, f, k=4.0, gate=True):
    big = f.cont & f.ar.notna() & (f.mv.abs() > k * f.ar)
    s = np.where(big, -np.sign(f.mv), 0.0)
    if gate:
        ok = ((f.mv > 0) & (d.close > f.vwap)) | ((f.mv < 0) & (d.close < f.vwap))
        s = np.where(ok, s, 0.0)
    return s


class Eng:
    """Runs ea_sim._sim_next (next-bar-open entries) with the EA entry rules on any bar DataFrame."""

    def __init__(self, d, B):
        self.d = d; self.B = B
        self.H = Harness(m1=d)
        gap = np.r_[np.diff(d.index.values).astype('timedelta64[s]').astype(np.int64), 10**6]
        nxt = np.r_[d.spread_usd.values[1:], 99.0]
        self.entry_ok = (gap == B * 60) & (nxt <= MAXSPR)
        self.spr = {'bar': d.spread_usd.values.astype(float), 'base': d.spread_usd.values + 0.05,
                    'wide': np.full(len(d), 0.30)}

    def prep(self, s, latency=0):
        s = np.sign(np.nan_to_num(np.asarray(s, float)))
        if latency: s = np.r_[np.zeros(latency), s[:-latency]]
        return np.where(self.entry_ok, s, 0).astype(np.int64)

    def run(self, s, N, sl, mo, spread='base', fill='FAIR', tp=1000.0, latency=0, cooldown=0, spr_arr=None):
        H = self.H; s = self.prep(s, latency)
        sp = self.spr[spread] if spr_arr is None else spr_arr
        dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, sp, H.tod, H.day, H.last, s, float(tp), float(sl),
                                             int(N), int(mo), FILL[fill], 0.0, 0.0, int(cooldown))
        days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=H.dates)
        T = pd.DataFrame({'entry': self.d.index[ti], 'ei': ti, 'xi': to, 'dir': tdr, 'pnl': tpn})
        return days, T


def sim_loop(d, s, N, sl, mo, entry_ok, add=0.05):
    """Plain-python re-implementation of the trade rules (no numba engine) for a cross-check."""
    o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    spr = d.spread_usd.values + add; tod = d.tod.values; last = d.last_of_session.values
    day = d.index.normalize().values; n = len(d)
    acc = []                                                  # (signal i, exit x, dir, pnl)
    for i in np.where(s != 0)[0]:
        if not entry_ok[i] or tod[i] < FIRST or tod[i] > LAST or last[i] or i >= n - 1: continue
        if sum(1 for a in acc if a[1] > i) >= mo: continue  # slots: positions whose exit bar is after i
        dr = int(np.sign(s[i]))
        e = o[i + 1] + spr[i + 1] if dr == 1 else o[i + 1]
        b = i + 1
        while True:
            stale = (b - i >= N) or tod[b] >= END_TOD or last[b] or b == n - 1 or day[b] != day[i]
            if dr == 1:
                if day[b] != day[i]: px = o[b]; break
                if o[b] <= e - sl: px = o[b]; break
                if l[b] <= e - sl: px = e - sl; break
                if stale: px = c[b]; break
            else:
                if day[b] != day[i]: px = o[b] + spr[b]; break
                if o[b] + spr[b] >= e + sl: px = o[b] + spr[b]; break
                if h[b] + spr[b] >= e + sl: px = e + sl; break
                if stale: px = c[b] + spr[b]; break
            b += 1
        acc.append((i, b, dr, (px - e) if dr == 1 else (e - px)))
    return pd.DataFrame(acc, columns=['ei', 'xi', 'dir', 'pnl'])


def stats(days, T, lo=None, hi=None, extra=0.0):
    ds = np.ones(len(days), bool); ts = np.ones(len(T), bool)
    if lo is not None: ds &= days.index >= pd.Timestamp(lo); ts &= (T.entry >= pd.Timestamp(lo)).values
    if hi is not None: ds &= days.index < pd.Timestamp(hi); ts &= (T.entry < pd.Timestamp(hi)).values
    p = days.pnl[ds] - extra * days.trades[ds]; t = T.pnl[ts] - extra
    eq = p.cumsum(); nd = max(len(p), 1)
    se = t.std(ddof=1) / np.sqrt(len(t)) if len(t) > 1 else np.nan
    return dict(per_day=p.mean(), trades_day=len(t) / nd, win=(t > 0).mean(), per_trade=t.mean(),
                days_ge5=(p >= 4.99).mean(), losing_days=(p < 0).mean(), worst_day=p.min(),
                worst_trade=t.min() if len(t) else np.nan, max_dd=(eq - eq.cummax()).min(), total=p.sum(),
                days=int(len(p)), trades=int(len(t)), long_share=(T.dir[ts] == 1).mean() if len(t) else np.nan,
                tstat=t.mean() / se if se and se > 0 else np.nan,
                breakeven_extra=t.mean() if len(t) else np.nan)


def rand_dirs(s, seed):
    r = np.where(np.random.default_rng(seed).random(len(s)) < .5, 1.0, -1.0)
    return np.where(np.asarray(s) != 0, r, 0.0)


def fmt(st):
    return (f"{st['per_day']:+.2f}/d {st['trades_day']:.2f}tr/d win {st['win']:.2f} {st['per_trade']:+.2f}/tr "
            f"t {st['tstat']:+.2f} >=5 {st['days_ge5']:.2f} lose {st['losing_days']:.2f} worstD {st['worst_day']:+.1f} "
            f"worstT {st['worst_trade']:+.1f} DD {st['max_dd']:+.1f} long {st['long_share']:.2f} n={st['trades']}")
