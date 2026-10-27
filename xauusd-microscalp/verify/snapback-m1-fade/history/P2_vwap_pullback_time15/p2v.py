"""Verifier library -- history / tail-risk lens -- for pick P2_vwap_pullback_time15 (family snapback-m1-fade).
Signal code written from the rule text (does NOT import the family's sb.py / evalx.py / picks.py).
Trades are simulated with the shared next-bar-open simulator ea/ea_sim._sim_next (imported read-only; nothing in
code/, ea/, data/ or families/ is modified). Run with NUMBA_CACHE_DIR in the scratchpad and PYTHONDONTWRITEBYTECODE=1.

Rule (M1): at the close of bar i
  ATR  = mean(High-Low) over the last 240 bars incl. bar i
  VWAP = sum((H+L+C)/3 * tick_volume) / sum(tick_volume) over the session's bars (since the 01:00 open) incl. bar i
  r3   = Close[i] - Close[i-3]
  signal if |r3| > 2.5 ATR and sign(Close[i]-VWAP) == -sign(r3)  -> trade direction = sign(Close[i]-VWAP)
  and the bar's recorded (= lowest) spread <= 15 points.
  Entry at the open of bar i+1 if it follows directly and its recorded spread <= 50 points; signal bar 01:05-22:29;
  max 3 open; no cooldown; time exit at the close of bar i+15; disaster stop $25; flat at 22:58 / session end.
Ports to M5/M15 use the same code with bar-count parameters (L, atr_n, hold) and gap = bar length.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from mlib import load_m1, SPLIT, FILL, random_like
from ea_sim import _sim_next

OUT = '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15/'
FAM = '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade/'
HALF = pd.Timestamp('2026-08-01')
M1START = pd.Timestamp('2026-06-26')
FILES = {'M5': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv',
         'M15': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv'}
BMIN = {'M1': 1, 'M5': 5, 'M15': 15}
P2 = dict(L=3, atr_n=240, k=2.5, gate='toward', sgate=0.15, sl=25.0, hold=15, mo=3)


def load_tf(tf):
    """Bars with spread_usd (recorded spread, zeros -> hour-of-day median, as mlib.load_m1), tod, last_of_session."""
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
    def __init__(self, m, tf='M1'):
        self.m = m; self.tf = tf; self.secs = 60 * BMIN[tf]
        dates = m.index.normalize()
        u, inv = np.unique(dates.values, return_inverse=True)
        self.dates = pd.DatetimeIndex(u); self.day = inv.astype(np.int64)
        self.o, self.h, self.l, self.c = (m[k].values.astype(np.float64) for k in ('open', 'high', 'low', 'close'))
        self.v = m.tick_volume.values.astype(np.float64)
        self.tod = m.tod.values.astype(np.int64)
        self.last = m.last_of_session.values.astype(np.bool_)
        self.rec = m.spread_usd.values.astype(np.float64)
        self._F = {}

    def feats(self, L, atr_n):
        key = (L, atr_n)
        if key not in self._F:
            c, h, l, v = self.c, self.h, self.l, self.v
            rng = h - l
            cs = np.r_[0.0, np.cumsum(rng)]
            atr = np.full(len(c), np.nan); atr[atr_n - 1:] = (cs[atr_n:] - cs[:-atr_n]) / atr_n
            typ = (h + l + c) / 3.0
            g = pd.Series(self.day)
            vv = np.where(self.tod >= 60, v, 0.0)      # session VWAP starts at the 01:00 open (older M5/M15 winter data has 00:xx bars)
            pv = pd.Series(typ * vv).groupby(g).cumsum().values; sv = pd.Series(vv).groupby(g).cumsum().values
            vw = pv / np.where(sv > 0, sv, np.nan)
            r = np.full(len(c), np.nan); r[L:] = c[L:] - c[:-L]
            self._F[key] = dict(atr=atr, vw=vw, r=r)
        return self._F[key]

    def signal(self, k=2.5, L=3, atr_n=240, gate='toward', sgate=0.15, side_only=False):
        F = self.feats(L, atr_n)
        r, atr, vw = F['r'], F['atr'], F['vw']
        side = np.sign(self.c - vw)
        with np.errstate(invalid='ignore'):
            hit = np.abs(r) > k * atr
        hit &= ~np.isnan(atr) & ~np.isnan(r)
        if gate == 'toward':
            hit &= side == -np.sign(r)
        elif gate == 'away':
            hit &= side == np.sign(r)
        if sgate > 0:
            hit &= self.rec <= sgate + 1e-9
        s = np.where(hit, -np.sign(r), 0.0)
        return np.nan_to_num(s)

    def ea_filter(self, s, max_spread=0.50, use_spread=True):
        s = np.sign(np.nan_to_num(np.asarray(s, float)))
        gap = np.r_[np.diff(self.m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 7]
        ok = gap == self.secs
        if use_spread:
            ok &= np.r_[self.rec[1:], 99.0] <= max_spread + 1e-9
        return np.where(ok, s, 0).astype(np.int64)

    def spread(self, model='base'):
        if isinstance(model, str):
            if model == 'bar': return self.rec.copy()
            if model == 'base': return self.rec + 0.05
            if model == 'wide': return np.full(len(self.c), 0.30)
            raise ValueError(model)
        model = np.asarray(model, np.float64)
        return np.full(len(self.c), float(model)) if model.ndim == 0 else model

    def run(self, sig, tp=1000.0, sl=25.0, hold=15, mo=3, spr='base', fill='FAIR', latency=0, filt=True,
            use_spread=True, cooldown=0):
        s = np.asarray(sig, float)
        if latency:
            s = np.r_[np.zeros(latency), s[:-latency]]
        s = self.ea_filter(s, use_spread=use_spread) if filt else np.sign(np.nan_to_num(s)).astype(np.int64)
        sp = self.spread(spr).astype(np.float64)
        dp, dt, ti, to, pn, dr = _sim_next(self.o, self.h, self.l, self.c, sp, self.tod, self.day, self.last, s,
                                           float(tp), float(sl), int(hold), int(mo), FILL[fill], 0.0, 0.0, int(cooldown))
        days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=self.dates)
        tr = pd.DataFrame({'entry': self.m.index[ti], 'ei': ti, 'xi': to, 'dir': dr, 'pnl': pn,
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
                worst_day=p.min() if len(p) else np.nan, worst_trade=t.pnl.min() if len(t) else np.nan,
                max_dd=(eq - eq.cummax()).min() if len(p) else np.nan, total=p.sum(), days=len(p),
                long_share=(t.dir == 1).mean() if len(t) else np.nan, n=len(t))


def line(name, r, w=40):
    return (f'{name:{w}s} {r["per_day"]:+7.2f}/day {r["trades_day"]:5.1f} tr/d win {r["win"]:.2f} {r["per_trade"]:+.3f}/tr '
            f'd>=5 {r["days_ge5"]:.2f} losing {r["losing_days"]:.2f} worstD {r["worst_day"]:+6.1f} worstT {r["worst_trade"]:+6.1f} '
            f'DD {r["max_dd"]:+7.1f} long {r["long_share"]:.2f} n {r["n"]}')
