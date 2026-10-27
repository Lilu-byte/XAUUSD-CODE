"""Verifier's own implementation of P1_snap_time3 (written from the rule text; does NOT import the family's sb.py/evalx.py).
Uses only the shared harness loader (mlib.load_m1 / Harness arrays) and the shared next-bar-open simulator ea_sim._sim_next,
plus an independent pure-python event simulator (sim_py) used for cross-checks and execution variants."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from mlib import load_m1, Harness, SPLIT, FILL, random_like, END_TOD, LAST_ENTRY_TOD, FIRST_ENTRY_TOD
from ea_sim import _sim_next

OUT = '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/repro/'
HALF = pd.Timestamp('2026-08-01')
TH, TP, SL, TO, MO = 7.0, 1000.0, 10.0, 3, 2


def raw_signal(close, th=TH):
    """Rule text: r3 = Close[i] - Close[i-3] (positional, like MT5 iClose shift); |r3| > th -> trade against it."""
    c = np.asarray(close, float)
    r3 = np.full(len(c), np.nan)
    r3[3:] = c[3:] - c[:-3]
    s = np.where(np.abs(r3) > th, -np.sign(r3), 0.0)
    return np.nan_to_num(s)


def entry_filter(m, s, max_spread=0.50, lat=0):
    """Entry happens at the first tick of bar e = i+1+lat. Allowed only if bar e opens exactly 60 s after bar e-1
    and the (recorded, zero-filled) spread of bar e <= max_spread. Returns the signal re-indexed so that the value sits
    on bar e-1 (the bar whose close is followed by the entry), as _sim_next expects."""
    s = np.asarray(s, float)
    if lat:
        s = np.r_[np.zeros(lat), s[:-lat]]
    t = m.index.values.astype('datetime64[s]').astype(np.int64)
    gap = np.r_[np.diff(t), 10 ** 6]
    sp = m.spread_usd.values
    nxt = np.r_[sp[1:], 99.0]
    return np.where((gap == 60) & (nxt <= max_spread + 1e-9), np.sign(s), 0).astype(np.int64)


class Rep:
    def __init__(self, m=None):
        self.m = load_m1() if m is None else m
        self.H = Harness(self.m)
        self.dates = self.H.dates

    def spr(self, model):
        if isinstance(model, (int, float)):
            return np.full(len(self.m), float(model))
        if model.startswith('base+'):
            return self.H._spr['base'] + float(model[5:])
        return self.H._spr[model]

    def run(self, s, spread='base', fill='FAIR', tp=TP, sl=SL, to=TO, mo=MO):
        H = self.H
        dp, dt, ti, tx, pn, dr = _sim_next(H.o, H.h, H.l, H.c, self.spr(spread), H.tod, H.day, H.last, np.asarray(s, np.int64),
                                           float(tp), float(sl), int(to), int(mo), FILL[fill], 0.0, 0.0, 0)
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
    eq = d.cumsum()
    pos = d[d > 0].sort_values(ascending=False)
    return dict(per_day=d.mean(), trades_day=len(t) / len(d), win=(t.pnl > 0).mean(), per_trade=t.pnl.mean(),
                days_ge5=(d >= 4.99).mean(), losing_days=(d < 0).mean(), worst_day=d.min(), best_day=d.max(),
                worst_trade=t.pnl.min(), max_dd=(eq - eq.cummax()).min(), total=d.sum(), days=len(d),
                long_share=(t.dir == 1).mean(), long_pnl=t.pnl[t.dir == 1].sum(), short_pnl=t.pnl[t.dir == -1].sum(),
                n_long=int((t.dir == 1).sum()), n_short=int((t.dir == -1).sum()),
                top5_share=d.sort_values(ascending=False).iloc[:5].sum() / d.sum() if d.sum() > 0 else np.nan,
                per_day_ex_top3=d.sort_values(ascending=False).iloc[3:].mean(),
                per_day_ex_top5=d.sort_values(ascending=False).iloc[5:].mean(),
                stop_share=(t.pnl <= -SL + 1e-6).mean())


def fmt(name, r):
    return (f"{name:28s} {r['per_day']:+7.2f}/day {r['trades_day']:5.1f} tr/d win {r['win']:.2f} {r['per_trade']:+.3f}/tr "
            f"d>=5 {r['days_ge5']:.2f} lose {r['losing_days']:.2f} worstD {r['worst_day']:+6.1f} worstT {r['worst_trade']:+6.1f} "
            f"DD {r['max_dd']:+7.1f} long {r['long_share']:.2f}")


def sim_py(o, h, l, c, t_ns, spr, tod, day, last, sig, sl=SL, hold=TO, mo=MO, exit_next_open=False, stop_slip=0.0):
    """Independent event simulator written from the rule text (pure python). sig[i] != 0 means: enter at the open of bar
    i+1 (already filtered). Long buys at ask = open + spr[i+1]; short sells at bid = open. Stop $sl from the entry price,
    checked on the bid (long) / ask (short) of bars i+1.., first touch fills at the stop (or at the bar open if it
    gaps through), minus stop_slip. Time exit at the close of bar i+hold (long at bid close, short at ask close =
    close + spr), or with exit_next_open at the open of bar i+hold+1 (if that bar is in the same session and not
    beyond the session end; otherwise at the close of bar i+hold). Forced exit at the close of a bar with
    tod >= 22:58 or the last bar of the session. Up to mo positions; a signal is dropped when mo are open."""
    n = len(c)
    pos = []          # [dir, entry_px, signal_idx]
    out = []
    for i in range(n):
        keep = []
        for p in pos:
            d, e, si = p
            if si >= i:
                keep.append(p); continue
            a = spr[i]
            px = None
            if d == 1:
                st = e - sl
                if o[i] <= st: px = o[i] - stop_slip
                elif l[i] <= st: px = st - stop_slip
            else:
                st = e + sl
                if o[i] + a >= st: px = o[i] + a + stop_slip
                elif h[i] + a >= st: px = st + stop_slip
            forced = (tod[i] >= END_TOD) or last[i] or (i == n - 1) or (day[i] != day[si])
            if px is None and day[i] != day[si]:
                px = o[i] if d == 1 else o[i] + a
            if px is None and (i - si >= hold or forced):
                if exit_next_open and not forced and i + 1 < n and day[i + 1] == day[i] and not last[i]:
                    px = o[i + 1] if d == 1 else o[i + 1] + spr[i + 1]
                else:
                    px = c[i] if d == 1 else c[i] + a
            if px is None:
                keep.append(p)
            else:
                out.append((si, i, d, (px - e) if d == 1 else (e - px)))
        pos = keep
        s = sig[i]
        if s != 0 and FIRST_ENTRY_TOD <= tod[i] <= LAST_ENTRY_TOD and not last[i] and i < n - 1 and len(pos) < mo:
            e = o[i + 1] + spr[i + 1] if s == 1 else o[i + 1]
            pos.append([int(s), e, i])
    return out
