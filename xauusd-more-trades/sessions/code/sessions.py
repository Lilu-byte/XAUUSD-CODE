"""One-trade-a-day session streams, built like GoldAsiaBreak (17 Oct 2026).

A stream is: a pair of levels per day (hi, lo), a time from which their break is watched, and a
direction rule. On the first closed bar at or after `start` whose close is outside [lo, hi]:
  'break' - trade the break's way          (close > hi -> buy, close < lo -> sell)
  'fade'  - trade the other way at once     (close > hi -> sell, close < lo -> buy)
  'fail'  - wait for the first later close back inside [lo, hi] (lo <= close <= hi), then trade
            against the break (a failed break above -> sell, below -> buy)
Entry on the next bar's open (it must be the very next bar, same day, opening before 22:30).
TP and SL a fixed $ distance from the fill, held broker-side (stop first if both in one bar, a
gap through either fills at the open), anything still open closes at the open of the first bar at
or after 22:45 (or the next open if the day ends earlier). One trade per stream per day; if the
first signal can't be traded (late, gap), the day is skipped, as GoldAsiaBreak does.

Levels:
  range(a, b): high/low of today's bars that start in [a, b) server time; usable once the bar
               starting at b - bar has closed; needs >= 2/3 of those bars (GoldAsiaBreak's rule).
  prevday:     yesterday's (previous trading day's) full high/low, needs >= 12 h of bars.
Costs as harness.asia(): spread $0.30 + slippage $0.10 on market orders (buy at bid + spread +
slip, sell at bid - slip; TP limits fill at the level, stops at the level - slip). Swap on any
overnight hold. scale=True (M15/H1 windows) multiplies distances and costs by price/4000 using
the signal bar's close and reports P&L in today's dollars.
On H1 bars, range starts are rounded down and range ends / start times up to the hour.
"""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/code')
import harness as H

CLOSE = 22 * 60 + 45
LAST_ENTRY = 15          # entries must open before CLOSE - LAST_ENTRY (22:30)


def hm(s):
    h, m = s.split(':')
    return int(h) * 60 + int(m)


class Bars:
    """Arrays for one timeframe (weekdays only, as the harness)."""
    _cache = {}

    def __new__(cls, tf):
        if tf in cls._cache: return cls._cache[tf]
        self = super().__new__(cls); cls._cache[tf] = self
        d = H.load(tf)
        self.tf, self.m = tf, H.MIN[tf]
        self.idx = d.index
        self.o, self.h, self.l, self.c = (d[k].values for k in ('open', 'high', 'low', 'close'))
        self.tod = (d.index.hour * 60 + d.index.minute).values
        dk = d.index.normalize()
        self.dates, self.first = np.unique(dk.values, return_index=True)   # first bar of each day
        self.last = np.r_[self.first[1:], len(d)]                           # one past last bar
        self.n = len(d)
        # end bar of a trade entered on day k: first bar of the day at/after CLOSE, else next day's first bar
        self.endbar = np.empty(len(self.dates), int)
        for k, (a, b) in enumerate(zip(self.first, self.last)):
            w = np.nonzero(self.tod[a:b] >= CLOSE)[0]
            self.endbar[k] = a + w[0] if len(w) else b
        return self


def snap(tf, a, b, s):
    """Range [a, b) and start time s in server minutes; on H1 widen to whole hours."""
    if H.MIN[tf] == 60:
        a = a // 60 * 60; b = -(-b // 60) * 60; s = -(-s // 60) * 60
    return a, b, s


def levels_range(B, a, b):
    """Per day hi, lo, ok of bars starting in [a, b)."""
    need = int(round((b - a) / B.m * 2 / 3))
    hi = np.full(len(B.dates), np.nan); lo = hi.copy(); ok = np.zeros(len(B.dates), bool)
    for k, (x, y) in enumerate(zip(B.first, B.last)):
        t = B.tod[x:y]; w = np.nonzero((t >= a) & (t < b))[0]
        if len(w) >= max(need, 1) and t[w[-1]] == b - B.m:
            hi[k] = B.h[x + w].max(); lo[k] = B.l[x + w].min(); ok[k] = True
    return hi, lo, ok


def levels_prevday(B):
    hi = np.full(len(B.dates), np.nan); lo = hi.copy(); ok = np.zeros(len(B.dates), bool)
    for k in range(1, len(B.dates)):
        x, y = B.first[k - 1], B.last[k - 1]
        if (y - x) * B.m >= 720 and (B.dates[k] - B.dates[k - 1]) <= np.timedelta64(4, 'D'):
            hi[k] = B.h[x:y].max(); lo[k] = B.l[x:y].min(); ok[k] = True
    return hi, lo, ok


def signals(B, levels, start, mode):
    """Entry bar index and direction per tradable day: list of (day k, i, dir)."""
    hi, lo, ok = levels
    out = []
    bar = np.timedelta64(B.m, 'm')
    for k in np.nonzero(ok)[0]:
        x, y = B.first[k], B.last[k]
        w = np.nonzero(B.tod[x:y] >= start)[0]
        if not len(w): continue
        js = x + w
        cc = B.c[js]
        out_ = np.nonzero((cc > hi[k]) | (cc < lo[k]))[0]
        if not len(out_): continue
        j0 = js[out_[0]]; brk = 1 if B.c[j0] > hi[k] else -1
        if mode == 'break': j, dr = j0, brk
        elif mode == 'fade': j, dr = j0, -brk
        elif mode == 'fail':
            later = np.arange(j0 + 1, y)
            back = np.nonzero((B.c[later] >= lo[k]) & (B.c[later] <= hi[k]))[0]
            if not len(back): continue
            j, dr = later[back[0]], -brk
        else: raise ValueError(mode)
        i = j + 1
        if i >= y or (B.idx.values[i] - B.idx.values[j]) != bar or B.tod[i] >= CLOSE - LAST_ENTRY:
            continue
        out.append((k, i, dr))
    return out


def simulate(B, sig, tp, sl, scale=False, spread=H.SPREAD, slip=H.SLIP, dirs=None, scale_at='signal'):
    """Trades for the signals (k, i, dir); dirs (array, same length) overrides the directions."""
    rows = []
    inbar = pd.Timedelta(minutes=B.m - 1)
    o, h, l, c, idx = B.o, B.h, B.l, B.c, B.idx
    for n_, (k, i, dr) in enumerate(sig):
        if dirs is not None: dr = int(dirs[n_])
        K = B.endbar[k]
        if K <= i: K = B.last[k]
        if K >= B.n: continue                       # still open at the end of the data
        sc = (c[i - 1] if scale_at == 'signal' else c[i]) / H.REF if scale else 1.0
        a, s_ = spread * sc, slip * sc
        kk = np.arange(i, K)
        if dr == 1:
            ent = o[i] + a + s_; SLp, TPp = ent - sl * sc, ent + tp * sc
            gSL = o[kk] <= SLp; gTP = o[kk] >= TPp; bSL = l[kk] <= SLp; bTP = h[kk] >= TPp
        else:
            ent = o[i] - s_; SLp, TPp = ent + sl * sc, ent - tp * sc
            gSL = o[kk] + a >= SLp; gTP = o[kk] + a <= TPp; bSL = h[kk] + a >= SLp; bTP = l[kk] + a <= TPp
        gSL[0] = gTP[0] = False                      # entry bar opens at the fill
        ev = gSL | gTP | bSL | bTP
        if ev.any():
            f = int(np.argmax(ev)); b_ = i + f
            if gSL[f]:   why, t, px = 'SL', idx[b_], (o[b_] - s_ if dr == 1 else o[b_] + a + s_)
            elif gTP[f]: why, t, px = 'TP', idx[b_], (o[b_] if dr == 1 else o[b_] + a)
            elif bSL[f]: why, t, px = 'SL', idx[b_] + inbar, (SLp - s_ if dr == 1 else SLp + s_)
            else:        why, t, px = 'TP', idx[b_] + inbar, TPp
        else:
            b_ = K
            if dr == 1:
                if o[b_] <= SLp: why, px = 'SL', o[b_] - s_
                elif o[b_] >= TPp: why, px = 'TP', o[b_]
                else: why, px = 'EOD', o[b_] - s_
            else:
                if o[b_] + a >= SLp: why, px = 'SL', o[b_] + a + s_
                elif o[b_] + a <= TPp: why, px = 'TP', o[b_] + a
                else: why, px = 'EOD', o[b_] + a + s_
            t = idx[b_]
        rows.append((idx[i], t, dr, ent, px, why, sc))
    T = pd.DataFrame(rows, columns=['entry_time', 'exit_time', 'dir', 'entry_px', 'exit_px', 'why', 'sc'])
    T['gross'] = (T.exit_px - T.entry_px) * T.dir / T.sc
    over = T.exit_time.dt.normalize() != T.entry_time.dt.normalize()
    T['swap'] = 0.0
    if over.any():
        T.loc[over, 'swap'] = [H.nights_swap(e, x, d) for e, x, d in T.loc[over, ['entry_time', 'exit_time', 'dir']].values]
    T['pnl'] = T.gross - T.swap
    return T


# ------------------------------------------------------------------ the setups tested
# name: (family, kind, range start, range end, watch-from)   kind 'range' or 'prevday'
SETUPS = {
    'LDN 09-15 >15:30':   ('london', 'range', '09:00', '15:00', '15:30'),
    'LDN 10-15 >15:30':   ('london', 'range', '10:00', '15:00', '15:30'),
    'LDN 09-15 >16:30':   ('london', 'range', '09:00', '15:00', '16:30'),
    'LDN 10-15 >16:30':   ('london', 'range', '10:00', '15:00', '16:30'),
    'LDN 09-15:30 >15:30': ('london', 'range', '09:00', '15:30', '15:30'),
    'LDN 09-16:30 >16:30': ('london', 'range', '09:00', '16:30', '16:30'),
    'NYO 15m':            ('nyopen', 'range', '16:30', '16:45', '16:45'),
    'NYO 30m':            ('nyopen', 'range', '16:30', '17:00', '17:00'),
    'NYO 60m':            ('nyopen', 'range', '16:30', '17:30', '17:30'),
    'USD 15m':            ('usdata', 'range', '15:30', '15:45', '15:45'),
    'USD 30m':            ('usdata', 'range', '15:30', '16:00', '16:00'),
    'USD 60m':            ('usdata', 'range', '15:30', '16:30', '16:30'),
    'PDHL >01:00':        ('prevday', 'prevday', None, None, '01:00'),
    'PDHL >09:00':        ('prevday', 'prevday', None, None, '09:00'),
    'PDHL >15:30':        ('prevday', 'prevday', None, None, '15:30'),
    'PDHL >16:30':        ('prevday', 'prevday', None, None, '16:30'),
}
MODES = ('break', 'fade', 'fail')
_lev = {}


def setup_signals(tf, name, mode):
    fam, kind, a, b, s = SETUPS[name]
    B = Bars(tf)
    if kind == 'range':
        a, b, s = snap(tf, hm(a), hm(b), hm(s))
        key = (tf, a, b)
        if key not in _lev: _lev[key] = levels_range(B, a, b)
        s = max(s, b)
    else:
        _, _, s = snap(tf, 0, 0, hm(s))
        key = (tf, 'pd')
        if key not in _lev: _lev[key] = levels_prevday(B)
    return signals(B, _lev[key], s, mode)


def stream(tf, name, mode, tp, sl, scale=None, dirs=None):
    """Trades of one stream on timeframe tf (scale defaults to True off M5)."""
    if scale is None: scale = tf != 'M5'
    return simulate(Bars(tf), setup_signals(tf, name, mode), tp, sl, scale=scale, dirs=dirs)


def window_trades(window, name, mode, tp, sl, dirs=None):
    return stream(H.WINDOWS[window][0], name, mode, tp, sl, dirs=dirs)
