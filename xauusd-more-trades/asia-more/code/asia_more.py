"""GoldAsiaBreak v1.10 with ways to trade more often (copy of harness.asia(), extended).

With every extension switched off, asia_x() is harness.asia() line for line in effect, and
verify.py checks that it reproduces H.asia('M5') and H.asia('M15', scale=True) trade for trade.

Extensions (all off by default):
- range_start: the range is today's bars from range_start to range_end (server minutes), so a
  second, later range can run as its own one-trade-a-day stream (e.g. 09:00-12:00, broken after
  12:00). min_bars defaults to 2/3 of the range's bars, as the EA (72 of 108 M5 bars).
- rearm ('tp' or 'any') + max_trades: after the day's trade closes (by TP only, or by TP or SL),
  wait for a FRESH break and trade it, up to max_trades trades a day. A fresh break is:
    fresh='reinside': a closed bar back inside the Asian range [low, high] (at or after the exit
                      bar), then the next closed bar outside it, traded that way;
    fresh='newext'  : a closed bar (at or after the exit bar) whose close is above the highest
                      high of today's earlier bars (from 00:00) -> buy, or below their lowest low
                      -> sell.
  The re-armed trades use rearm_tp / rearm_sl (default: the same TP / SL).
- sar: after a stop-out (the day's trade hits its SL the same day), trade once the opposite way:
    sar='break': the next closed bar beyond the OTHER side of the Asian range, next bar's open;
    sar='now'  : at the next bar's open straight away.
  With sar_tp / sar_sl (default: same TP / SL).
All trades keep the EA's rules: entry on the next bar's open after the signal close, between
range end and 15 minutes before the close time; TP/SL from the fill, held broker-side (stop first
if both fall in one bar, gaps fill at the open); close at the 22:45 bar's open; a trade left from
an earlier day closes at the next open. A break that can't be traded (missing bar) ends the day.
"""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/code')
import harness as H
from harness import load, nights_swap, MIN, SPREAD, SLIP, REF

CLOSE = 22 * 60 + 45


def _prep(tf, scale, range_start, range_end, min_bars):
    d = load(tf)
    m = MIN[tf]
    if min_bars is None: min_bars = int(round((range_end - range_start) / m * 2 / 3))
    idx = d.index
    o, h, l, c = (d[k].values for k in ('open', 'high', 'low', 'close'))
    tod = (idx.hour * 60 + idx.minute).values
    date = idx.normalize(); dkey = date.values
    sc = (c / REF) if scale else np.ones(len(c))
    inr = (tod >= range_start) & (tod < range_end)
    a_ = d[inr].assign(t=tod[inr])
    g = a_.groupby(a_.index.normalize())
    R = pd.DataFrame({'hi': g.high.max(), 'lo': g.low.min(), 'n': g.size(), 'last': g.t.max()})
    R['ok'] = (R.n >= min_bars) & (R['last'] == range_end - m)
    rhi = R.hi.reindex(date).values; rlo = R.lo.reindex(date).values
    rok = R.ok.reindex(date).fillna(False).values.astype(bool)
    # highest high / lowest low of today's EARLIER bars (from 00:00), known at bar j's close
    hs = pd.Series(h).groupby(dkey).cummax(); ls = pd.Series(l).groupby(dkey).cummin()
    prev_hi = hs.groupby(dkey).shift(1).values; prev_lo = ls.groupby(dkey).shift(1).values
    return dict(d=d, m=m, idx=idx, o=o, h=h, l=l, c=c, tod=tod, dkey=dkey, sc=sc,
                rhi=rhi, rlo=rlo, rok=rok, prev_hi=prev_hi, prev_lo=prev_lo)


def _finish(rows):
    t = pd.DataFrame(rows)
    if len(t) == 0:
        return pd.DataFrame(columns=['entry_time', 'dir', 'entry_px', 'sc', 'kind', 'n', 'exit_time', 'why',
                                     'exit_px', 'gross', 'swap', 'pnl'])
    t['gross'] = np.where(t.dir == 1, t.exit_px - t.entry_px, t.entry_px - t.exit_px) / t.sc
    t['swap'] = [nights_swap(e, x, k) for e, x, k in zip(t.entry_time, t.exit_time, t.dir)]
    t['pnl'] = t.gross - t.swap
    return t


def asia_x(tf='M5', tp=5.0, sl=50.0, scale=False, range_start=0, range_end=540, close=CLOSE, last_entry=15,
           min_bars=None, rearm=None, max_trades=1, fresh='reinside', rearm_tp=None, rearm_sl=None,
           sar=None, sar_tp=None, sar_sl=None, direction=None, spread=SPREAD, slip=SLIP):
    P = _prep(tf, scale, range_start, range_end, min_bars)
    idx, o, h, l, c, tod, dkey, sc = (P[k] for k in ('idx', 'o', 'h', 'l', 'c', 'tod', 'dkey', 'sc'))
    rhi, rlo, rok, phi, plo = P['rhi'], P['rlo'], P['rok'], P['prev_hi'], P['prev_lo']
    m = P['m']
    rtp = tp if rearm_tp is None else rearm_tp; rsl = sl if rearm_sl is None else rearm_sl
    stp = tp if sar_tp is None else sar_tp; ssl = sl if sar_sl is None else sar_sl
    bar = pd.Timedelta(minutes=m); inbar = pd.Timedelta(minutes=m - 1)
    sp = spread
    rows = []; pos = 0; ent_i = 0; e_sc = 1.0; SLp = TPp = 0.0
    cur = None; state = 'first'; ntr = 0; sar_used = False; sar_dir = 0

    def on_exit(why, i):
        # what the day does after a trade closes (only for a trade opened today, closed today)
        nonlocal state, sar_used, sar_dir
        if dkey[ent_i] != dkey[i] or why in ('EOD', 'next open'):
            return
        if sar and why == 'SL' and not sar_used:
            state = 'sar_now' if sar == 'now' else 'sar'; sar_used = True; sar_dir = -rows[-1]['dir']
        elif rearm and ntr < max_trades and (rearm == 'any' or why == 'TP'):
            state = 'need_inside' if fresh == 'reinside' else 'ready'
        else:
            state = 'off'

    for i in range(1, len(c)):
        day = dkey[i]
        if day != cur:
            cur = day; state = 'first'; ntr = 0; sar_used = False
        if pos != 0:
            ex = None; s_ = slip * e_sc; a = sp * e_sc
            stale = dkey[i] != dkey[ent_i]
            if pos == 1:
                if o[i] <= SLp: ex, px = 'SL', o[i] - s_
                elif o[i] >= TPp: ex, px = 'TP', o[i]
                elif tod[i] >= close or stale: ex, px = ('EOD' if not stale else 'next open'), o[i] - s_
            else:
                if o[i] + a >= SLp: ex, px = 'SL', o[i] + a + s_
                elif o[i] + a <= TPp: ex, px = 'TP', o[i] + a
                elif tod[i] >= close or stale: ex, px = ('EOD' if not stale else 'next open'), o[i] + a + s_
            if ex:
                rows[-1].update(exit_time=idx[i], why=ex, exit_px=px); pos = 0
                on_exit(ex, i)
                continue
        if pos == 0 and state != 'off' and range_end < tod[i] < close - last_entry and rok[i]:
            j = i - 1
            if dkey[j] == day and tod[j] >= range_end:
                sig = 0; kind = None
                if state == 'first':
                    sig = 1 if c[j] > rhi[i] else (-1 if c[j] < rlo[i] else 0); kind = 'first'
                elif state == 'need_inside':
                    if rlo[i] <= c[j] <= rhi[i]: state = 'ready'
                elif state == 'ready':
                    kind = 'rearm'
                    if fresh == 'reinside':
                        sig = 1 if c[j] > rhi[i] else (-1 if c[j] < rlo[i] else 0)
                    else:
                        sig = 1 if c[j] > phi[j] else (-1 if c[j] < plo[j] else 0)
                elif state == 'sar':
                    kind = 'sar'
                    if sar_dir == 1 and c[j] > rhi[i]: sig = 1
                    elif sar_dir == -1 and c[j] < rlo[i]: sig = -1
                elif state == 'sar_now':
                    kind = 'sar'; sig = sar_dir
                if sig:
                    state = 'off'                       # re-armed (or not) when this trade closes
                    on_time = (idx[i] - idx[j]) == bar
                    dr = sig
                    if direction is not None and kind == 'first': dr = direction[day]
                    if on_time:
                        ntr += 1
                        ttp, tsl = {'first': (tp, sl), 'rearm': (rtp, rsl), 'sar': (stp, ssl)}[kind]
                        pos = dr; ent_i = i; e_sc = sc[i]; s_ = slip * e_sc
                        if dr == 1: ent = o[i] + sp * e_sc + s_; SLp, TPp = ent - tsl * e_sc, ent + ttp * e_sc
                        else: ent = o[i] - s_; SLp, TPp = ent + tsl * e_sc, ent - ttp * e_sc
                        rows.append(dict(entry_time=idx[i], dir=dr, entry_px=ent, sc=e_sc, kind=kind, n=ntr,
                                         tp=ttp, sl=tsl))
        if pos != 0:
            a = sp * e_sc; s_ = slip * e_sc; ex = None
            if pos == 1:
                if l[i] <= SLp: ex, px = 'SL', SLp - s_
                elif h[i] >= TPp: ex, px = 'TP', TPp
            else:
                if h[i] + a >= SLp: ex, px = 'SL', SLp + s_
                elif l[i] + a <= TPp: ex, px = 'TP', TPp
            if ex:
                rows[-1].update(exit_time=idx[i] + inbar, why=ex, exit_px=px); pos = 0
                on_exit(ex, i)
    if pos: rows.pop()
    return _finish(rows)


def sim_fixed(tf, entries, scale=False, close=CLOSE, spread=SPREAD, slip=SLIP):
    """Simulate each trade on its own from a list of (entry_time, dir, tp, sl), with the EA's exits
    (used for random-direction checks: same entry times, same TP/SL/exit, direction swapped)."""
    d = load(tf); m = MIN[tf]
    idx = d.index; o, h, l, c = (d[k].values for k in ('open', 'high', 'low', 'close'))
    tod = (idx.hour * 60 + idx.minute).values; dkey = idx.normalize().values
    sc = (c / REF) if scale else np.ones(len(c))
    pos_of = pd.Series(np.arange(len(idx)), index=idx)
    inbar = pd.Timedelta(minutes=m - 1)
    rows = []
    for et, dr, ttp, tsl in entries:
        i0 = pos_of[et]; e_sc = sc[i0]; s_ = slip * e_sc; a = spread * e_sc
        if dr == 1: ent = o[i0] + a + s_; SLp, TPp = ent - tsl * e_sc, ent + ttp * e_sc
        else: ent = o[i0] - s_; SLp, TPp = ent + tsl * e_sc, ent - ttp * e_sc
        r = dict(entry_time=et, dir=dr, entry_px=ent, sc=e_sc)
        for i in range(i0, len(c)):
            ex = None
            if i > i0:
                stale = dkey[i] != dkey[i0]
                if dr == 1:
                    if o[i] <= SLp: ex, px = 'SL', o[i] - s_
                    elif o[i] >= TPp: ex, px = 'TP', o[i]
                    elif tod[i] >= close or stale: ex, px = 'EOD', o[i] - s_
                else:
                    if o[i] + a >= SLp: ex, px = 'SL', o[i] + a + s_
                    elif o[i] + a <= TPp: ex, px = 'TP', o[i] + a
                    elif tod[i] >= close or stale: ex, px = 'EOD', o[i] + a + s_
                if ex: r.update(exit_time=idx[i], why=ex, exit_px=px); break
            if dr == 1:
                if l[i] <= SLp: ex, px = 'SL', SLp - s_
                elif h[i] >= TPp: ex, px = 'TP', TPp
            else:
                if h[i] + a >= SLp: ex, px = 'SL', SLp + s_
                elif l[i] + a <= TPp: ex, px = 'TP', TPp
            if ex: r.update(exit_time=idx[i] + inbar, why=ex, exit_px=px); break
        if 'exit_time' in r: rows.append(r)
    return _finish(rows)


def window_tf_scale(window):
    tf = H.WINDOWS[window][0]
    return tf, tf != 'M5'
