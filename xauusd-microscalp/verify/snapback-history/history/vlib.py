"""Verifier library (independent re-implementation of pick C and its ports).
Only reads shared code: mlib.Harness (arrays), ea_sim._sim_next (next-bar-open engine), hlib.load_tf (loader).

Generalised rule, for any bar size B (minutes):
  R_j   = range of the M15-equivalent window ending at bar j: max(high[j-w+1..j]) - min(low[j-w+1..j]),
          w = 15/B bars (w = 1 on M15, 3 on M5, 15 on M1)
  AR_i  = mean of R_j over the L bars j = i-L .. i-1  (L = 32*w: the 8 hours before bar i)
  move  = close[i] - close[i-n], n = 2*w (30 minutes), bars i-n..i consecutive
  SELL if move > k*AR_i and close[i] > VWAP_i; BUY if move < -k*AR_i and close[i] < VWAP_i (k = 4)
  VWAP_i = cumsum((H+L+C)/3 * tick_volume) / cumsum(tick_volume) from the day's first bar
  entry: open of bar i+1 if it follows directly and its recorded spread <= $0.50; signal tod 01:05-22:29
  exit: close of bar i+N, N = 2*w (30 minutes); disaster stop sl; flat at 22:58 / last bar of session
On M15 with w = 1 this is exactly the colleague's pick C.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-history')
from mlib import Harness, FILL, load_m1
from ea_sim import _sim_next
import hlib

MAX_SPREAD = 0.50
COMM = 0.07


def finish(d, bar_min=15):
    """Add spread_usd (zero spreads -> same month/hour median, as hlib), tod, last_of_session
    (next bar more than max(30, 1.5 x bar) minutes away)."""
    d = d.copy()
    sp = d.spread.copy(); nz = sp > 0
    key = d.index.to_period('M').astype(str) + '_' + d.index.hour.astype(str)
    mm = sp[nz].groupby(key[nz]).median(); mh = sp[nz].groupby(d.index.hour[nz]).median()
    z = ~nz
    fill = pd.Series(key[z], index=d.index[z]).map(mm)
    fill = fill.fillna(pd.Series(d.index[z].hour, index=d.index[z]).map(mh))
    sp[z] = fill.values
    d['spread_usd'] = sp * 0.01
    d['tod'] = d.index.hour * 60 + d.index.minute
    nxt = d.index.to_series().shift(-1)
    d['last_of_session'] = ((nxt - d.index.to_series()) > pd.Timedelta(minutes=max(30, 1.5 * bar_min))) | nxt.isna()
    return d


def load(tf):
    if tf in ('M5', 'M15'): return hlib.load_tf(tf)
    if tf == 'M1': return load_m1()
    raise ValueError(tf)


def resample_offset(d5, offset_min):
    """M15 bars built from M5 bars, window start shifted by offset_min (0, 5, 10). Spread = min of the M5
    recorded spreads (MT5 records the lowest), volume summed. Only complete windows (3 M5 bars)."""
    raw = hlib.pd.read_csv(hlib.FILES['M5'])
    raw.index = pd.to_datetime(raw.time, format='%Y.%m.%d %H:%M')
    raw = raw[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].astype(float)
    raw = raw[raw.index.dayofweek < 5]
    g = raw.resample('15min', offset=f'{offset_min}min', label='left', closed='left')
    out = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(), 'close': g.close.last(),
                        'tick_volume': g.tick_volume.sum(), 'spread': g.spread.min(), 'cnt': g.open.count()})
    out = out[out.cnt == 3].drop(columns='cnt')
    return finish(out)


def features(d, B, L15=32, w=None, L=None):
    w = max(1, 15 // B) if w is None else w
    L = L15 * w if L is None else L
    rngw = d.high.rolling(w).max() - d.low.rolling(w).min()
    ar = rngw.rolling(L).mean().shift(1)
    day = d.index.normalize()
    tp = (d.high + d.low + d.close) / 3
    vw = (tp * d.tick_volume).groupby(day).cumsum() / d.tick_volume.groupby(day).cumsum()
    step = d.index.to_series().diff() == pd.Timedelta(minutes=B)
    return pd.DataFrame({'ar': ar, 'vwap': vw, 'step': step}, index=d.index), w


def signal(d, f, n, k, gate=1):
    mv = d.close - d.close.shift(n)
    ok = (f.step.rolling(n).sum() == n) & f.ar.notna()
    big = ok & (mv.abs() > k * f.ar)
    s = np.where(big, -np.sign(mv), 0.0)
    if gate:
        keep = ((mv > 0) & (d.close > f.vwap)) | ((mv < 0) & (d.close < f.vwap))
        s = np.where(keep, s, 0.0)
    return np.nan_to_num(s)


class Eng:
    def __init__(self, d, B):
        self.d = d; self.B = B
        self.H = Harness(m1=d)
        gap = np.r_[np.diff(d.index.values).astype('timedelta64[s]').astype(np.int64), 10**6]
        nxt = np.r_[d.spread_usd.values[1:], 99.0]
        self.entry_ok = (gap == B * 60) & (nxt <= MAX_SPREAD)
        self.gap_ok = gap == B * 60
        self.spr = dict(self.H._spr)

    def add_spread(self, name, arr):
        self.spr[name] = np.asarray(arr, np.float64)

    def run(self, s, N, sl, mo=3, spread='base', fill='FAIR', tp=1000.0, latency=0, spread_filter=True, cooldown=0):
        H = self.H
        s = np.sign(np.nan_to_num(np.asarray(s, float)))
        if latency: s = np.r_[np.zeros(latency), s[:-latency]]
        ok = self.entry_ok if spread_filter else self.gap_ok
        s = np.where(ok, s, 0).astype(np.int64)
        dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, self.spr[spread], H.tod, H.day, H.last, s,
                                             float(tp), float(sl), int(N), int(mo), FILL[fill], 0.0, 0.0, int(cooldown))
        days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=H.dates)
        T = pd.DataFrame({'entry': self.d.index[ti], 'ei': ti, 'xi': to, 'dir': tdr, 'pnl': tpn})
        return days, T


def stats(days, T, lo=None, hi=None, extra=0.0):
    sel = np.ones(len(days), bool); ts = np.ones(len(T), bool)
    if lo is not None: sel &= days.index >= pd.Timestamp(lo); ts &= (T.entry >= pd.Timestamp(lo)).values
    if hi is not None: sel &= days.index < pd.Timestamp(hi); ts &= (T.entry < pd.Timestamp(hi)).values
    p = days.pnl[sel] - extra * days.trades[sel]; t = T.pnl[ts] - extra
    eq = p.cumsum(); nd = max(len(p), 1)
    tt = T[ts]
    return dict(per_day=p.mean(), trades_day=len(t) / nd, win=(t > 0).mean() if len(t) else np.nan,
                per_trade=t.mean() if len(t) else np.nan, days_ge5=(p >= 4.99).mean(), losing_days=(p < 0).mean(),
                worst_day=p.min(), worst_trade=t.min() if len(t) else np.nan, max_dd=(eq - eq.cummax()).min(),
                trades=len(t), days=len(p), long_share=(tt.dir == 1).mean() if len(t) else np.nan,
                tstat=t.mean() / t.std() * np.sqrt(len(t)) if len(t) > 2 else np.nan,
                breakeven_extra=t.mean() if len(t) else np.nan)


def fmt(st):
    return (f"{st['per_day']:+.3f}/d {st['trades_day']:.2f}tr/d win {st['win']:.2f} {st['per_trade']:+.3f}/tr "
            f"t{st['tstat']:+.2f} n{st['trades']} ge5 {st['days_ge5']:.3f} lose {st['losing_days']:.3f} "
            f"wd {st['worst_day']:+.1f} wt {st['worst_trade']:+.1f} dd {st['max_dd']:+.1f} long {st['long_share']:.2f}")
