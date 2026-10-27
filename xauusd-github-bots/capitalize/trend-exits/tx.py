"""Trend-exit simulator (approach B: let winners run), same cost conventions as ../../code/gbt.py.

One position at a time, optionally pyramided to 2 units (0.01 lot each, $1 per $1 move per unit).
A signal decided on closed bar i fills at the open of bar i+1 (long at ask + slip, short at bid - slip).
Exits, in order on each bar:
  1. at the open: exit signal from the previous closed bar, or a gap through the stop
  2. (pyramid add fills at the open here, if it was triggered on the previous close and step 1 did not exit)
  3. inside the bar: stop first, then target (stop assumed first if both in one bar)
  4. at the close (active from the next bar): trailing/chandelier stop update, breakeven, pyramid trigger
An intrabar stop-out blocks a new entry on that same bar (the engine in gbt.py allows it; that is
temporally impossible because the entry would be at an earlier price than the stop).
Swap $0.126 long / $0.046 short per unit per night, triple Wednesday, exactly as gbt.py.
"""
import sys
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import gbt  # noqa: E402

SPREAD, SLIP, SWAP_L, SWAP_S = gbt.SPREAD, gbt.SLIP, gbt.SWAP_L, gbt.SWAP_S


@njit(cache=True)
def _sim(o, h, l, c, dayid, dow, sig, sl_d, tp_d, trail_m, atr_l, trail_start, xl, xs,
         add_trig, add_be_off, max_units, max_bars, spread, slip, swl, sws, be_trig, allow_same):
    n = len(o)
    out = np.zeros((n * 2, 9))
    k = 0
    pos = 0; nu = 0; e1 = 0.0; e2 = 0.0; i1 = 0; i2 = 0; sl = 0.0; tp = 0.0; best = 0.0
    a_ent = 0.0; tm = 0.0; tst = 0.0; pend_add = False; added = False
    for i in range(1, n):
        stopped_intrabar = False
        if pos != 0:
            px = 0.0; why = 0
            ask_o = o[i] + spread
            # 1. exits at the open
            if (pos == 1 and xl[i - 1]) or (pos == -1 and xs[i - 1]):
                px = o[i] - slip if pos == 1 else ask_o + slip; why = 4
            elif max_bars > 0 and i - i1 >= max_bars:
                px = o[i] - slip if pos == 1 else ask_o + slip; why = 5
            elif sl > 0 and pos == 1 and o[i] <= sl:
                px = o[i] - slip; why = 1
            elif sl > 0 and pos == -1 and ask_o >= sl:
                px = ask_o + slip; why = 1
            elif tp > 0 and pos == 1 and o[i] >= tp:
                px = o[i]; why = 2
            elif tp > 0 and pos == -1 and ask_o <= tp:
                px = ask_o; why = 2
            # 2. pyramid add at the open
            if why == 0 and pend_add:
                e2 = o[i] + spread + slip if pos == 1 else o[i] - slip
                i2 = i; nu = 2; added = True
            pend_add = False
            # 3. inside the bar
            if why == 0:
                if pos == 1:
                    if sl > 0 and l[i] <= sl: px = sl - slip; why = 1
                    elif tp > 0 and h[i] >= tp: px = tp; why = 2
                else:
                    if sl > 0 and h[i] + spread >= sl: px = sl + slip; why = 1
                    elif tp > 0 and l[i] + spread <= tp: px = tp; why = 2
                if why != 0: stopped_intrabar = True
            if why != 0:
                for u in range(nu):
                    ent = e1 if u == 0 else e2
                    ei = i1 if u == 0 else i2
                    g = (px - ent) if pos == 1 else (ent - px)
                    nights = 0.0
                    for j in range(ei + 1, i + 1):
                        if dayid[j] != dayid[j - 1]:
                            nights += 3.0 if dow[j - 1] == 2 else 1.0
                    sw = nights * (swl if pos == 1 else sws)
                    out[k, 0] = ei; out[k, 1] = i; out[k, 2] = pos; out[k, 3] = ent; out[k, 4] = px
                    out[k, 5] = g; out[k, 6] = sw; out[k, 7] = why; out[k, 8] = u + 1; k += 1
                pos = 0; nu = 0
            else:
                # 4. close-of-bar updates
                if pos == 1:
                    if h[i] > best: best = h[i]
                    fav = best - e1
                    if be_trig > 0 and fav >= be_trig * a_ent and sl < e1: sl = e1
                    if tm > 0 and fav >= tst * a_ent:
                        ns = best - tm * atr_l[i]
                        if ns > sl: sl = ns
                    if max_units > 1 and not added and (c[i] - e1) >= add_trig * a_ent:
                        pend_add = True
                        if sl < e1 + add_be_off: sl = e1 + add_be_off
                else:
                    lo = l[i] + spread
                    if lo < best: best = lo
                    fav = e1 - best
                    if be_trig > 0 and fav >= be_trig * a_ent and (sl > e1 or sl == 0.0): sl = e1
                    if tm > 0 and fav >= tst * a_ent:
                        ns = best + tm * atr_l[i]
                        if sl == 0.0 or ns < sl: sl = ns
                    if max_units > 1 and not added and (e1 - (c[i] + spread)) >= add_trig * a_ent:
                        pend_add = True
                        if sl == 0.0 or sl > e1 - add_be_off: sl = e1 - add_be_off
        # new entry from the signal on closed bar i-1
        if pos == 0 and sig[i - 1] != 0 and atr_l[i - 1] > 0 and (allow_same or not stopped_intrabar):
            d_ = int(sig[i - 1])
            ent = o[i] + spread + slip if d_ == 1 else o[i] - slip
            pos = d_; nu = 1; e1 = ent; i1 = i; added = False; pend_add = False
            a_ent = atr_l[i - 1]; tm = trail_m[i - 1]; tst = trail_start
            sl = ent - sl_d[i - 1] * d_ if sl_d[i - 1] > 0 else 0.0
            tp = ent + tp_d[i - 1] * d_ if tp_d[i - 1] > 0 else 0.0
            best = ent
            # same-bar stop/target check (stop first)
            px = 0.0; why = 0
            if d_ == 1:
                if sl > 0 and l[i] <= sl: px = sl - slip; why = 1
                elif tp > 0 and h[i] >= tp: px = tp; why = 2
            else:
                if sl > 0 and h[i] + spread >= sl: px = sl + slip; why = 1
                elif tp > 0 and l[i] + spread <= tp: px = tp; why = 2
            if why != 0:
                g = (px - ent) if d_ == 1 else (ent - px)
                out[k, 0] = i; out[k, 1] = i; out[k, 2] = d_; out[k, 3] = ent; out[k, 4] = px
                out[k, 5] = g; out[k, 6] = 0.0; out[k, 7] = why; out[k, 8] = 1; k += 1
                pos = 0; nu = 0
            else:
                if d_ == 1:
                    if h[i] > best: best = h[i]
                    fav = best - e1
                    if be_trig > 0 and fav >= be_trig * a_ent and sl < e1: sl = e1
                    if tm > 0 and fav >= tst * a_ent:
                        ns = best - tm * atr_l[i]
                        if ns > sl: sl = ns
                else:
                    lo = l[i] + spread
                    if lo < best: best = lo
                    fav = e1 - best
                    if be_trig > 0 and fav >= be_trig * a_ent and (sl > e1 or sl == 0.0): sl = e1
                    if tm > 0 and fav >= tst * a_ent:
                        ns = best + tm * atr_l[i]
                        if sl == 0.0 or ns < sl: sl = ns
    return out[:k]


REASONS = {1: 'stop', 2: 'target', 4: 'signal', 5: 'time'}


def tsim(d, sig, atr_live, sl=0.0, tp=0.0, trail_m=0.0, trail_start=0.0, exit_long=None, exit_short=None,
         add_trig=0.0, add_be_off=0.0, max_units=1, max_bars=0, be_trig=0.0, spread=SPREAD, slip=SLIP,
         swap_l=SWAP_L, swap_s=SWAP_S, allow_same=False):
    """sig/sl/tp/trail_m arrays (or scalars) decided on each bar's close. sl/tp are $ distances.
    trail_m: chandelier multiple; stop = best price since entry - trail_m * atr_live (live, closed bar),
    only once the trade has moved trail_start * ATR(entry) in favour. add_trig: add the 2nd unit
    when the close is add_trig * ATR(entry) beyond entry 1; the shared stop then goes to entry1 + add_be_off."""
    n = len(d)
    arr = lambda x, dt=float: np.broadcast_to(np.nan_to_num(np.asarray(x, dt)), (n,)).astype(dt).copy()
    _, dayid = np.unique(d.index.normalize().values, return_inverse=True)
    out = _sim(d.open.values, d.high.values, d.low.values, d.close.values, dayid.astype(np.int64),
               d.index.dayofweek.values.astype(np.int64), arr(sig), arr(sl), arr(tp), arr(trail_m), arr(atr_live),
               float(trail_start), arr(False if exit_long is None else exit_long, np.bool_),
               arr(False if exit_short is None else exit_short, np.bool_), float(add_trig), float(add_be_off),
               int(max_units), int(max_bars), float(spread), float(slip), float(swap_l), float(swap_s), float(be_trig), bool(allow_same))
    t = pd.DataFrame(out, columns=['ei', 'xi', 'dir', 'entry', 'exit', 'gross', 'swap', 'why', 'unit'])
    t['entry_time'] = d.index[t.ei.astype(int)]; t['exit_time'] = d.index[t.xi.astype(int)]
    t['pnl'] = t.gross - t.swap
    t['why'] = t.why.astype(int).map(REASONS)
    return t


def mtm_daily(t, d):
    """Mark-to-market daily equity change (open trades valued at each day's last close, bid for longs,
    ask for shorts; swap charged when the trade closes, as in the closed-trade numbers)."""
    days = pd.DatetimeIndex(np.unique(d.index.normalize()))
    c = d.close.values; n = len(d)
    open_val = np.zeros(n)
    for r in t.itertuples():
        a, b = int(r.ei), int(r.xi)
        if b > a:
            v = (c[a:b] - r.entry) if r.dir == 1 else (r.entry - (c[a:b] + SPREAD))
            open_val[a:b] += v
    realized = np.zeros(n)
    np.add.at(realized, t.xi.astype(int).values, t.pnl.values)
    eq = pd.Series(np.cumsum(realized) + open_val, index=d.index)
    eq_d = eq.groupby(d.index.normalize()).last().reindex(days).ffill().fillna(0)
    return eq_d


def summary(t, d, start=None, end=None, label=''):
    """$/day over trading days of d in [start, end); trades counted by ENTRY time inside the window."""
    m = np.ones(len(d), bool)
    if start is not None: m &= d.index >= pd.Timestamp(start)
    if end is not None: m &= d.index < pd.Timestamp(end)
    dd = d[m]
    tt = t[(t.entry_time >= dd.index[0]) & (t.entry_time <= dd.index[-1])]
    days = pd.DatetimeIndex(np.unique(dd.index.normalize()))
    p = tt.groupby(tt.exit_time.dt.normalize()).pnl.sum()
    p = p.reindex(days.union(p.index), fill_value=0.0)
    eq = p.cumsum(); mo = p.groupby(p.index.to_period('M')).sum()
    yrs = len(days) / 252.0
    pos = tt[tt.unit == 1] if 'unit' in tt else tt
    return dict(label=label, trades=len(pos), units=len(tt), per_day=round(p.sum() / len(days), 2),
                win=round((pos.pnl > 0).mean() * 100, 1) if len(pos) else np.nan,
                pf=round(tt.pnl[tt.pnl > 0].sum() / max(1e-9, -tt.pnl[tt.pnl < 0].sum()), 2) if len(tt) else np.nan,
                max_dd=round((eq - eq.cummax()).min(), 0), tr_yr=round(len(pos) / yrs, 1),
                pos_months=f'{(mo > 0).sum()}/{len(mo)}', total=round(p.sum(), 0), days=len(days))


def by_year(t, d):
    p = gbt.daily(t, d)
    return p.groupby(p.index.year).mean().round(2)


def coinflip(d, sig, runs=40, seed=1, **kw):
    rng = np.random.default_rng(seed); s = np.asarray(sig, float); nz = s != 0; res = []
    for _ in range(runs):
        r = s.copy(); r[nz] = np.where(rng.random(nz.sum()) < .5, 1.0, -1.0)
        res.append(r)
    return res
