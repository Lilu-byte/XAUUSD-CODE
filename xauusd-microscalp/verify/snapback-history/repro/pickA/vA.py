"""Independent re-implementation of pick A (M15 snap-back fade, VWAP-gated, 60-min time exit) from the written rule.
Does NOT import the colleague's hlib / signal code. Uses only mlib.Harness (array holder) and ea_sim._sim_next (scorer).

Rule (as written): at the close of M15 bar i
  AR32  = mean(high-low) over bars i-32..i-1
  move  = close[i] - close[i-2], bars i-2,i-1,i consecutive (15 min apart)
  VWAP  = cumsum(tp*tick_volume)/cumsum(tick_volume) over the server date's bars <= i, tp=(H+L+C)/3
  SELL if move > 4*AR32 and close > VWAP ; BUY if move < -4*AR32 and close < VWAP
  entry at open of bar i+1 if it starts exactly 15 min after bar i and its spread <= 50 points
  no TP, disaster stop $25, exit at close of bar i+4, max 3 open, signal-bar time 01:05..22:29 (sim constants)
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from mlib import Harness, FILL
from ea_sim import _sim_next

M15_FILE = '/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv'
TRAIN = ('2022-07-01', '2025-01-01')
TEST = ('2025-01-01', '2026-10-10')


def load_m15(path=M15_FILE, zero_fill='year_hour'):
    d = pd.read_csv(path)
    d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    d = d[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].astype(float)
    d = d[d.index.dayofweek < 5].copy()
    sp = d.spread.copy(); nz = sp > 0
    if zero_fill == 'year_hour':
        key = d.index.year.astype(str) + '_' + d.index.hour.astype(str)
    else:
        key = pd.Index(d.index.hour.astype(str))
    med = sp[nz].groupby(np.asarray(key)[nz]).median()
    hmed = sp[nz].groupby(d.index.hour[nz]).median()
    z = ~nz
    f = pd.Series(np.asarray(key)[z]).map(med).values
    f = np.where(np.isnan(f), pd.Series(d.index.hour[z]).map(hmed).values, f)
    sp[z] = f
    d['spread_usd'] = sp * 0.01
    d['raw_zero'] = z
    d['tod'] = d.index.hour * 60 + d.index.minute
    t = d.index.to_series()
    nxt = t.shift(-1)
    d['last_of_session'] = ((nxt - t) > pd.Timedelta(minutes=30)) | nxt.isna()
    return d


def sig_A(d, L=32, n=2, k=4.0, gate=True):
    """Signal at the close of each bar, computed with bars <= i only. Returns float array of -1/0/+1."""
    h = d.high.values; l = d.low.values; c = d.close.values; v = d.tick_volume.values
    N = len(d)
    rng = h - l
    cs = np.r_[0.0, np.cumsum(rng)]
    ar = np.full(N, np.nan)
    idx = np.arange(L, N)
    ar[idx] = (cs[idx] - cs[idx - L]) / L                       # mean of rng[i-L..i-1]
    tmin = d.index.values.astype('datetime64[m]').astype(np.int64)
    gap = np.r_[np.nan, np.diff(tmin)]                          # minutes since previous bar
    # bars i-2,i-1,i consecutive  <=> gap[i]==15 and gap[i-1]==15
    ok2 = np.zeros(N, bool); ok2[2:] = (gap[2:] == 15) & (gap[1:-1] == 15)
    ok = ok2 if n == 2 else (gap == 15)
    mv = np.full(N, np.nan); mv[n:] = c[n:] - c[:-n]
    # session VWAP per server date
    day = d.index.normalize().values
    tp = (h + l + c) / 3.0
    df = pd.DataFrame({'pv': tp * v, 'v': v, 'day': day})
    vw = (df.groupby('day').pv.cumsum() / df.groupby('day').v.cumsum()).values
    s = np.zeros(N)
    big_up = ok & ~np.isnan(ar) & (mv > k * ar)
    big_dn = ok & ~np.isnan(ar) & (mv < -k * ar)
    if gate:
        big_up &= c > vw; big_dn &= c < vw
    s[big_up] = -1.0; s[big_dn] = 1.0
    return s, ar


class Sim:
    def __init__(self, d):
        self.d = d
        self.H = Harness(m1=d)
        tmin = d.index.values.astype('datetime64[m]').astype(np.int64)
        self.gap_next = np.r_[np.diff(tmin), 10**6]               # minutes from bar i to bar i+1
        self.spr_raw = d.spread_usd.values.astype(np.float64)
        self.spr_next = np.r_[self.spr_raw[1:], 99.0]

    def entry_ok(self, max_spread=0.50, strict_lt=False):
        sp_ok = (self.spr_next < max_spread) if strict_lt else (self.spr_next <= max_spread)
        return (self.gap_next == 15) & sp_ok

    def spread(self, model):
        s = self.spr_raw
        if model == 'bar': return s.copy()
        if model == 'base': return s + 0.05
        if isinstance(model, (int, float)): return np.full(len(s), float(model))
        if isinstance(model, np.ndarray): return model.astype(np.float64)
        raise ValueError(model)

    def run(self, sig, sl=25.0, N=4, max_open=3, tp=1000.0, fill='FAIR', spread='base', latency=0,
            max_spread=0.50, strict_lt=False):
        s = np.sign(np.nan_to_num(np.asarray(sig, float)))
        if latency:
            s = np.r_[np.zeros(latency), s[:-latency]]
        s = np.where(self.entry_ok(max_spread, strict_lt), s, 0).astype(np.int64)
        H = self.H
        dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, self.spread(spread), H.tod, H.day, H.last, s,
                                             float(tp), float(sl), int(N), int(max_open), FILL[fill], 0.0, 0.0, 0)
        days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=H.dates)
        T = pd.DataFrame({'entry': self.d.index[ti], 'ei': ti, 'xi': to, 'dir': tdr, 'pnl': tpn,
                          'bars': np.where(to >= 0, to - ti, -1)})
        return days, T


def per(days, T, lo, hi, extra=0.0):
    ds = days[(days.index >= pd.Timestamp(lo)) & (days.index < pd.Timestamp(hi))]
    ts = T[(T.entry >= pd.Timestamp(lo)) & (T.entry < pd.Timestamp(hi))]
    p = ds.pnl - extra * ds.trades; t = ts.pnl - extra
    eq = p.cumsum()
    pos = p[p > 0].sort_values(ascending=False)
    tot = p.sum()
    tstat = t.mean() / (t.std(ddof=1) / np.sqrt(len(t))) if len(t) > 2 else np.nan
    return dict(per_day=p.mean(), trades_day=len(t) / max(len(p), 1), win=(t > 0).mean(), per_trade=t.mean(),
                days_ge5=(p >= 4.99).mean(), losing_days=(p < 0).mean(), worst_day=p.min(), worst_trade=t.min(),
                max_dd=(eq - eq.cummax()).min(), total=tot, days=len(p), trades=len(t),
                long_share=(ts.dir == 1).mean(), long_pt=ts.pnl[ts.dir == 1].mean(), short_pt=ts.pnl[ts.dir == -1].mean(),
                n_long=int((ts.dir == 1).sum()), n_short=int((ts.dir == -1).sum()),
                long_total=ts.pnl[ts.dir == 1].sum(), short_total=ts.pnl[ts.dir == -1].sum(),
                top5_share=pos.head(5).sum() / tot if tot > 0 else np.nan, top5_sum=pos.head(5).sum(),
                tstat=tstat, sd_trade=t.std(ddof=1), active_days=int((ds.trades > 0).sum()))
