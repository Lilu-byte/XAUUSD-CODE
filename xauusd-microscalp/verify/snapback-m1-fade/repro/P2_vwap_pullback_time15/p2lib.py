"""Adversarial verifier, pick P2_vwap_pullback_time15 (family snapback-m1-fade).
Written from the RULE TEXT only: does not import the family's sb.py / evalx.py / picks.py.
Uses the shared loader (mlib.load_m1, Harness arrays) and the shared next-bar-open simulator ea_sim._sim_next,
plus an independent pure-python event simulator (pysim) for cross-checks and execution variants.

Rule (as written): at the close of M1 bar i
  ATR   = mean(High-Low) of the last 240 M1 bars incl. bar i
  VWAP  = sum(typ x tick_volume)/sum(tick_volume), typ = (H+L+C)/3, over the session's bars (since 01:00) incl. bar i
  r3    = Close[i] - Close[i-3]
  signal if |r3| > K x ATR and sign(Close[i]-VWAP) == -sign(r3); direction = sign(Close[i]-VWAP)
  and the bar's lowest spread (MT5 recorded spread) <= 15 points ($0.15)
Entry at the open of bar i+1 if it follows bar i by exactly 60 s and the spread of bar i+1 <= $0.50; signal bar
01:05-22:29; up to 3 open, no cooldown; pure time exit at the close of bar i+15; disaster stop $25; flat at 22:58 /
session end.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from mlib import load_m1, Harness, SPLIT, FILL, random_like, END_TOD, LAST_ENTRY_TOD, FIRST_ENTRY_TOD
from ea_sim import _sim_next

OUT = '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/repro/P2_vwap_pullback_time15/'
HALF = pd.Timestamp('2026-08-01')
K, ATR_N, SGATE, TP, SL, HOLD, MO = 2.5, 240, 0.15, 1000.0, 25.0, 15, 3


def signal(o, h, l, c, v, dates, spr_usd, k=K, atr_n=ATR_N, sgate=SGATE):
    """Plain-numpy loop-free version. dates: per-bar calendar date (session id). Returns +1/-1/0 per bar."""
    n = len(c)
    rng = h - l
    cs = np.r_[0.0, np.cumsum(rng)]
    atr = np.full(n, np.nan)
    atr[atr_n - 1:] = (cs[atr_n:] - cs[:-atr_n]) / atr_n
    typ = (h + l + c) / 3.0
    pv = typ * v
    # session cumulative sums (reset at each new date)
    vw = np.empty(n)
    sp = 0.0; sv = 0.0; prev = None
    for i in range(n):
        if dates[i] != prev:
            sp = 0.0; sv = 0.0; prev = dates[i]
        sp += pv[i]; sv += v[i]
        vw[i] = sp / sv if sv > 0 else c[i]
    r3 = np.full(n, np.nan)
    r3[3:] = c[3:] - c[:-3]
    with np.errstate(invalid='ignore'):
        hit = (np.abs(r3) > k * atr) & (np.sign(c - vw) == -np.sign(r3)) & (np.sign(r3) != 0)
        if sgate is not None:
            hit &= spr_usd <= sgate + 1e-9
    s = np.where(hit, np.sign(c - vw), 0.0)
    return np.nan_to_num(s), atr, vw, r3


def signal_df(m, **kw):
    return signal(m.open.values, m.high.values, m.low.values, m.close.values, m.tick_volume.values.astype(float),
                  m.index.normalize().values, m.spread_usd.values, **kw)


def entry_filter(m, s, max_spread=0.50, lat=0, strict_lt=False):
    """Entry at the first tick of bar e = i+1+lat. Allowed only if bar e opens exactly 60 s after bar e-1 and the
    recorded (zero-filled) spread of bar e <= max_spread (< if strict_lt). Signal re-indexed onto bar e-1."""
    s = np.asarray(s, float)
    if lat:
        s = np.r_[np.zeros(lat), s[:-lat]]
    t = m.index.values.astype('datetime64[s]').astype(np.int64)
    gap = np.r_[np.diff(t), 10 ** 6]
    sp = m.spread_usd.values
    nxt = np.r_[sp[1:], 99.0]
    ok = (nxt < max_spread - 1e-9) if strict_lt else (nxt <= max_spread + 1e-9)
    return np.where((gap == 60) & ok, np.sign(s), 0).astype(np.int64)


class Rep:
    def __init__(self, m=None):
        self.m = load_m1() if m is None else m
        self.H = Harness(self.m)
        self.dates = self.H.dates

    def spr(self, model):
        H = self.H
        if isinstance(model, (int, float)): return np.full(len(self.m), float(model))
        if model.startswith('base+'): return H._spr['base'] + float(model[5:])
        if model.startswith('flat'): return np.full(len(self.m), float(model[4:]))
        return H._spr[model]

    def run(self, s, spread='base', fill='FAIR', tp=TP, sl=SL, hold=HOLD, mo=MO):
        H = self.H
        dp, dt, ti, tx, pn, dr = _sim_next(H.o, H.h, H.l, H.c, self.spr(spread), H.tod, H.day, H.last,
                                           np.asarray(s, np.int64), float(tp), float(sl), int(hold), int(mo), FILL[fill],
                                           0.0, 0.0, 0)
        days = pd.Series(dp, index=self.dates)
        T = pd.DataFrame({'ei': ti, 'xi': tx, 'entry': self.m.index[ti], 'dir': dr, 'pnl': pn})
        return days, T


def stats(days, T, period, fee=0.0):
    if period == 'train': sel = days.index < SPLIT
    elif period == 'test': sel = days.index >= SPLIT
    elif period == 'A': sel = days.index < HALF
    elif period == 'B': sel = (days.index >= HALF) & (days.index < SPLIT)
    else: sel = np.ones(len(days), bool)
    d = days[sel].copy()
    t = T[T.entry.dt.normalize().isin(d.index)].copy()
    if fee:
        t['pnl'] = t.pnl - fee
        d = d - fee * t.groupby(t.entry.dt.normalize()).size().reindex(d.index, fill_value=0)
    eq = d.cumsum(); ds = d.sort_values(ascending=False)
    return dict(per_day=d.mean(), trades_day=len(t) / len(d), win=(t.pnl > 0).mean(), per_trade=t.pnl.mean(),
                days_ge5=(d >= 4.99).mean(), losing_days=(d < 0).mean(), worst_day=d.min(), best_day=d.max(),
                worst_trade=t.pnl.min(), best_trade=t.pnl.max(), max_dd=(eq - eq.cummax()).min(), total=d.sum(),
                days=len(d), n_trades=len(t), long_share=(t.dir == 1).mean(),
                long_pnl=t.pnl[t.dir == 1].sum(), short_pnl=t.pnl[t.dir == -1].sum(),
                n_long=int((t.dir == 1).sum()), n_short=int((t.dir == -1).sum()),
                top5_share=ds.iloc[:5].sum() / d.sum() if d.sum() > 0 else np.nan,
                per_day_ex_top3=ds.iloc[3:].mean(), per_day_ex_top5=ds.iloc[5:].mean(),
                stop_share=(t.pnl <= -SL + 1e-6).mean(), day_sd=d.std(ddof=1),
                t_stat=d.mean() / (d.std(ddof=1) / np.sqrt(len(d))))


def fmt(name, r):
    return (f"{name:30s} {r['per_day']:+7.2f}/day {r['trades_day']:5.1f} tr/d win {r['win']:.2f} {r['per_trade']:+.3f}/tr "
            f"d>=5 {r['days_ge5']:.2f} lose {r['losing_days']:.2f} worstD {r['worst_day']:+6.1f} worstT {r['worst_trade']:+6.1f} "
            f"DD {r['max_dd']:+7.1f} long {r['long_share']:.2f}")


def pysim(o, h, l, c, spr, tod, day, last, sig, sl=SL, hold=HOLD, mo=MO, exit_next_open=False, stop_slip=0.0):
    """Independent pure-python event simulator from the rule text. sig[i] != 0 (already entry-filtered) = enter at the
    open of bar i+1: long at ask = open + spr[i+1], short at bid = open. Disaster stop $sl from the entry price on the bid
    (long) / ask (short): gap-through fills at the bar open, else at the stop (minus stop_slip). Time exit at the close of
    bar i+hold (long at bid close, short at ask close = close + spr); with exit_next_open, at the open of bar i+hold+1 when
    that bar is the same session (else the close). Forced exit at the close of a bar with tod >= 22:58, the last bar
    of a session or the last bar of the data; a new date closes at its open. Up to mo positions; extra signals dropped."""
    n = len(c); pos = []; out = []
    for i in range(n):
        keep = []
        for p in pos:
            d, e, si = p
            if si >= i: keep.append(p); continue
            a = spr[i]; px = None
            if day[i] != day[si]:
                px = o[i] if d == 1 else o[i] + a
            elif d == 1:
                st = e - sl
                if o[i] <= st: px = o[i] - stop_slip
                elif l[i] <= st: px = st - stop_slip
            else:
                st = e + sl
                if o[i] + a >= st: px = o[i] + a + stop_slip
                elif h[i] + a >= st: px = st + stop_slip
            forced = (tod[i] >= END_TOD) or last[i] or (i == n - 1)
            if px is None and (i - si >= hold or forced):
                if exit_next_open and not forced and i + 1 < n and day[i + 1] == day[i]:
                    px = o[i + 1] if d == 1 else o[i + 1] + spr[i + 1]
                else:
                    px = c[i] if d == 1 else c[i] + a
            if px is None: keep.append(p)
            else: out.append((si, i, d, (px - e) if d == 1 else (e - px)))
        pos = keep
        s = sig[i]
        if s != 0 and FIRST_ENTRY_TOD <= tod[i] <= LAST_ENTRY_TOD and not last[i] and i < n - 1 and len(pos) < mo:
            pos.append([int(s), o[i + 1] + spr[i + 1] if s == 1 else o[i + 1], i])
    return out


def pysim_frame(R, sig, spread='base', **kw):
    H = R.H
    out = pysim(H.o, H.h, H.l, H.c, R.spr(spread), H.tod, H.day, H.last, np.asarray(sig, np.int64), **kw)
    T = pd.DataFrame(out, columns=['ei', 'xi', 'dir', 'pnl']).sort_values(['ei', 'xi']).reset_index(drop=True)
    T['entry'] = R.m.index[T.ei.values]
    days = T.groupby(T.entry.dt.normalize()).pnl.sum().reindex(R.dates, fill_value=0.0)
    return days, T
