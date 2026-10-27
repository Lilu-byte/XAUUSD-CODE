"""Idle-time streams next to the pair (GoldAllAgree v1.10 + GoldAsiaBreak v1.10), 17 Oct 2026.

A stream here is one small bracket trade a day (TP $5-8, stop $30-50, close at 22:45 server),
taken on a second intraday signal, optionally only while the pair is idle:

  gate='none'   ungated: trade every signal.
  gate='entry'  skip the signal if, at the fill bar's open, GoldAllAgree is in a position or
                GoldAsiaBreak has an open trade (either EA may still open one later).
  gate='strict' as 'entry', and also close the stream's trade at the open of the first bar at
                which either EA is in a position, so the stream never overlaps the pair.

Which bars are "busy" comes from the pair's own trades on the same timeline (H.pair_parts):
a bar is busy for an EA when one of its trades has entry_time <= bar open < exit_time.

The bracket engine copies harness.asia()'s fill and exit rules: market entry on the open of the
bar after the signal bar (long pays spread $0.30 + slippage $0.10, short pays slippage), TP/SL set
from the fill, stop first if both are inside one bar, gaps through a level fill at the open, close
at the open of the first bar at/after 22:45 (or the next open for a trade left from an earlier
day), swap on nights held. On M15/H1 every $ distance and cost is multiplied by price/4000 and
P&L is reported in today's dollars (scale=True), as pair_parts does; on M5 the dollars are fixed.
check_engine.py shows that fed GoldAsiaBreak's entries this engine reproduces H.asia() exactly.

Signals (each gives at most one entry a day; the signal is known at a bar close and filled on
the next bar's open, which must start exactly when the signal bar ends):
  move(start, end, mode, thr): price change from the open of the bar starting at `start` to the
      close of the bar ending at `end` (server minutes; on H1 start rounds down and end rounds
      up to the hour). mode=+1 trades with the move, -1 against it; skip if |move| < thr
      (thr in $, scaled on M15/H1). NY first hour = move(16:30, 17:30); London = move(10:00, 15:30).
  h1ema(T): sign of EMA20 - EMA80 of H1 closes, last H1 bar closed by T, traded at T.
  pullback(need_h1, t0, t1): H4 EMA20 > EMA80 (from the last closed H4 bar) -> look for the first
      bar of the day closing in [t0, t1] whose low reaches the H1 EMA20 (value from the last H1
      bar closed before that bar opened) while the bar before it (same day) had its low above
      the H1 EMA20 known at its own open;
      buy at the next open. Mirror for H4 down (high reaches it from below; sell). need_h1=True
      also needs H1 EMA20 vs EMA80 to agree with H4 at the signal bar's close.
"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/code')
import numpy as np, pandas as pd
import harness as H
from lib import ema, align, MIN, load as raw_load

CLOSE = 22 * 60 + 45
LAST_ENTRY = 15          # no entries in the last 15 minutes before CLOSE (as GoldAsiaBreak)
_bars, _busy, _parts = {}, {}, {}


class Bars:
    def __init__(self, tf):
        d = H.load(tf)
        self.tf, self.m = tf, MIN[tf]
        self.idx = d.index
        self.o, self.h, self.l, self.c = (d[k].values for k in ('open', 'high', 'low', 'close'))
        self.tod = (d.index.hour * 60 + d.index.minute).values
        self.dkey = d.index.normalize().values
        self.close_time = d.index + pd.Timedelta(minutes=self.m)


def bars(tf):
    if tf not in _bars: _bars[tf] = Bars(tf)
    return _bars[tf]


def tf_of(window):
    return H.WINDOWS[window][0]


def pair(window):
    """The pair's trades on the window's timeline (same as H.pair_parts(window))."""
    tf = tf_of(window)
    if tf not in _parts:
        _parts[tf] = H.pair_parts(window)
    return _parts[tf]


def busy(tf):
    """(allagree_busy, asia_busy) boolean arrays: EA has a position at that bar's open."""
    if tf not in _busy:
        B = bars(tf); ix = B.idx.values
        win = {'M5': 'pair', 'M15': 'm15_train', 'H1': 'h1_old'}[tf]
        P = pair(win); out = []
        for k in ('AllAgree', 'AsiaBreak'):
            a = np.zeros(len(ix), bool)
            for e, x in zip(P[k].entry_time.values, P[k].exit_time.values):
                a[np.searchsorted(ix, e, 'left'):np.searchsorted(ix, x, 'left')] = True
            out.append(a)
        _busy[tf] = tuple(out)
    return _busy[tf]


# ------------------------------------------------------------------ bracket engine
def bracket(tf, ent, dirs, tp=5.0, sl=50.0, scale=True, gate='none', close=CLOSE,
            spread=H.SPREAD, slip=H.SLIP):
    """Simulate one bracket trade per entry bar index in `ent` (direction `dirs`, +1/-1).
    Entries while a previous trade is still open are skipped."""
    B = bars(tf)
    o, h, l, c, tod, dkey, idx = B.o, B.h, B.l, B.c, B.tod, B.dkey, B.idx
    if tf == 'M5': scale = False
    sc = c / H.REF if scale else np.ones(len(c))
    inbar = pd.Timedelta(minutes=B.m - 1)
    if gate != 'none':
        ba, bb = busy(tf); bz = ba | bb
    n = len(c); rows = []; free_from = 0
    for i, dr in zip(np.asarray(ent, int), np.asarray(dirs, int)):
        if i < free_from or i >= n: continue
        if gate != 'none' and bz[i]: continue
        e_sc = sc[i]; s_ = slip * e_sc; a = spread * e_sc
        if dr == 1: px0 = o[i] + a + s_; SLp, TPp = px0 - sl * e_sc, px0 + tp * e_sc
        else: px0 = o[i] - s_; SLp, TPp = px0 + sl * e_sc, px0 - tp * e_sc
        ex = None; k = i
        while True:
            if k > i:   # checks at this bar's open
                stale = dkey[k] != dkey[i]
                forced = gate == 'strict' and bz[k]
                if dr == 1:
                    if o[k] <= SLp: ex = ('SL', idx[k], o[k] - s_)
                    elif o[k] >= TPp: ex = ('TP', idx[k], o[k])
                    elif tod[k] >= close or stale or forced:
                        ex = ('EOD' if not (stale or forced) else ('next open' if stale else 'pair busy'), idx[k], o[k] - s_)
                else:
                    if o[k] + a >= SLp: ex = ('SL', idx[k], o[k] + a + s_)
                    elif o[k] + a <= TPp: ex = ('TP', idx[k], o[k] + a)
                    elif tod[k] >= close or stale or forced:
                        ex = ('EOD' if not (stale or forced) else ('next open' if stale else 'pair busy'), idx[k], o[k] + a + s_)
                if ex: break
            # inside the bar, stop first
            if dr == 1:
                if l[k] <= SLp: ex = ('SL', idx[k] + inbar, SLp - s_)
                elif h[k] >= TPp: ex = ('TP', idx[k] + inbar, TPp)
            else:
                if h[k] + a >= SLp: ex = ('SL', idx[k] + inbar, SLp + s_)
                elif l[k] + a <= TPp: ex = ('TP', idx[k] + inbar, TPp)
            if ex: break
            k += 1
            if k >= n: break
        if not ex: break                       # still open at the end of the data: drop it
        why, xt, xp = ex
        rows.append(dict(entry_time=idx[i], exit_time=xt, dir=int(dr), entry_px=px0, exit_px=xp, sc=e_sc, why=why))
        free_from = k + 1                      # as asia(): the exit bar takes no new entry
    t = pd.DataFrame(rows, columns=['entry_time', 'exit_time', 'dir', 'entry_px', 'exit_px', 'sc', 'why'])
    t['gross'] = np.where(t.dir == 1, t.exit_px - t.entry_px, t.entry_px - t.exit_px) / t.sc
    t['swap'] = [H.nights_swap(e, x, k) for e, x, k in zip(t.entry_time, t.exit_time, t.dir)]
    t['pnl'] = t.gross - t.swap
    return t


# ------------------------------------------------------------------ signals
def _entry_ok(B, j):
    """Signal at the close of bar j -> fill at bar j+1's open, which must follow without a gap,
    be the same day, and leave at least LAST_ENTRY minutes before the close."""
    i = j + 1
    return (i < len(B.c)) & (B.idx[np.minimum(i, len(B.c) - 1)] == B.close_time[j]) & \
           (B.dkey[np.minimum(i, len(B.c) - 1)] == B.dkey[j]) & (B.tod[np.minimum(i, len(B.c) - 1)] < CLOSE - LAST_ENTRY)


def sig_move(tf, start, end, mode=1, thr=0.0, scale=True):
    B = bars(tf); m = B.m
    if tf == 'H1': start = start // 60 * 60; end = -(-end // 60) * 60
    tod, dkey = B.tod, B.dkey
    df = pd.DataFrame({'d': dkey, 'tod': tod, 'o': B.o, 'c': B.c, 'j': np.arange(len(tod))})
    first = df[df.tod == start].drop_duplicates('d').set_index('d')
    last = df[df.tod == end - m].drop_duplicates('d').set_index('d')
    J = first.join(last, how='inner', lsuffix='0', rsuffix='1')
    J = J[_entry_ok(B, J.j1.values)]
    mv = J.c1 - J.o0
    s = (J.c1 / H.REF) if (scale and tf != 'M5') else 1.0
    J = J[mv.abs() >= thr * s]; mv = mv.loc[J.index]
    J = J[mv != 0]; mv = mv.loc[J.index]
    return J.j1.values + 1, (np.sign(mv.values) * mode).astype(int)


def _hi_series(tf_hi, fast=20, slow=80):
    d = raw_load(tf_hi)
    return d, ema(d.close, fast), ema(d.close, slow)


def sig_h1ema(tf, T):
    B = bars(tf); m = B.m
    d1, f, s = _hi_series('H1')
    tr = align(d1, 'H1', B.close_time, np.sign(f - s).values).fillna(0).values
    j = np.where(B.tod == T - m)[0]
    j = j[_entry_ok(B, j)]
    j = j[tr[j] != 0]
    return j + 1, tr[j].astype(int)


def sig_pullback(tf, need_h1=False, t0=10 * 60, t1=20 * 60):
    B = bars(tf); m = B.m
    d4, f4, s4 = _hi_series('H4')
    tr4 = align(d4, 'H4', B.close_time, np.sign(f4 - s4).values).fillna(0).values
    d1, f1, s1 = _hi_series('H1')
    tr1 = align(d1, 'H1', B.close_time, np.sign(f1 - s1).values).fillna(0).values
    lvl = align(d1, 'H1', B.idx, f1.values).values          # H1 EMA20 known at each bar's open
    ct = B.tod + m
    n = len(B.c); j = np.arange(1, n)
    same = B.dkey[j] == B.dkey[j - 1]
    up = (tr4[j] > 0) & (B.l[j] <= lvl[j]) & (B.l[j - 1] > lvl[j - 1]) & same
    dn = (tr4[j] < 0) & (B.h[j] >= lvl[j]) & (B.h[j - 1] < lvl[j - 1]) & same
    if need_h1:
        up &= tr1[j] > 0; dn &= tr1[j] < 0
    ok = (up | dn) & (ct[j] >= t0) & (ct[j] <= t1) & np.isfinite(lvl[j])
    jj = j[ok]; dd = np.where(up[ok], 1, -1)
    jj_ok = _entry_ok(B, jj)
    jj, dd = jj[jj_ok], dd[jj_ok]
    first = ~pd.Series(B.dkey[jj]).duplicated().values    # first setup of each day only
    return jj[first] + 1, dd[first]


def signal(tf, spec):
    kind = spec['kind']
    if kind == 'move': return sig_move(tf, spec['start'], spec['end'], spec['mode'], spec.get('thr', 0.0))
    if kind == 'h1ema': return sig_h1ema(tf, spec['T'])
    if kind == 'pullback': return sig_pullback(tf, spec['need_h1'], spec.get('t0', 600), spec.get('t1', 1200))
    raise ValueError(kind)


def stream(window, spec, tp, sl, gate, dirs=None):
    tf = tf_of(window)
    ent, dr = signal(tf, spec)
    if dirs is not None: dr = dirs
    return bracket(tf, ent, dr, tp=tp, sl=sl, scale=True, gate=gate)


def pair_trades(window):
    P = pair(window)
    return pd.concat([P['AllAgree'][['entry_time', 'exit_time', 'dir', 'pnl']],
                      P['AsiaBreak'][['entry_time', 'exit_time', 'dir', 'pnl']]], ignore_index=True)
