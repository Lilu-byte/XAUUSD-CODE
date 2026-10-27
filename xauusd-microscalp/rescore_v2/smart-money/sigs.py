"""Smart-money-concept micro setups on XAUUSD M1 (and M5 built from M1).
Every signal is an int8 array (+1 long / -1 short / 0) aligned to M1 rows, decided at that
row's CLOSE using only bars <= that row. HTF (M5) signals are placed on the M1 row whose close
equals the M5 bar's close (or the first M1 row after it if that minute is missing).
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
from numba import njit
from mlib import resample, SPLIT


# ---------------------------------------------------------------- helpers
def arrs(d):
    return (d.open.values.astype(float), d.high.values.astype(float),
            d.low.values.astype(float), d.close.values.astype(float))


def htf_bars(m1, minutes):
    """Closed M-minute bars from M1 plus, for each, the M1 row at which it is known."""
    b = resample(m1, minutes)
    known = b.index + pd.Timedelta(minutes=minutes - 1)        # label of the last M1 bar inside
    pos = m1.index.searchsorted(known, side='left')             # first M1 row with label >= that
    ok = pos < len(m1)
    return b[ok], pos[ok]


def place(m1, pos, s_htf):
    """Put HTF-bar signals onto M1 rows (pos = M1 row where each HTF bar is known)."""
    out = np.zeros(len(m1), np.int8)
    s = np.asarray(s_htf)
    nz = s != 0
    out[pos[nz]] = s[nz]
    return out


def same_day_mask(m1):
    d = m1.index.normalize().values
    return d


# ---------------------------------------------------------------- liquidity sweep
def sweep(o, h, l, c, N, depth=0.0, need_color=False, close_frac=0.0):
    """Wick takes out the prior N-bar high (low) and the bar closes back below (above) it -> reversal.
    depth: min $ beyond the level; close_frac: close must be back inside by >= close_frac * (h-l).
    need_color: bearish close for a high sweep (bullish for a low sweep). Returns reversal direction."""
    H = pd.Series(h).shift(1).rolling(N).max().values
    L = pd.Series(l).shift(1).rolling(N).min().values
    rng = np.maximum(h - l, 1e-9)
    sh = (h >= H + depth) & (c < H - close_frac * rng)
    sl = (l <= L - depth) & (c > L + close_frac * rng)
    if need_color:
        sh &= c < o; sl &= c > o
    s = np.zeros(len(c), np.int8)
    s[sh] = -1; s[sl] = 1
    s[sh & sl] = 0
    return s


def breakout(o, h, l, c, N):
    """Close beyond the prior N-bar high/low (continuation direction)."""
    H = pd.Series(h).shift(1).rolling(N).max().values
    L = pd.Series(l).shift(1).rolling(N).min().values
    s = np.zeros(len(c), np.int8)
    s[c > H] = 1; s[c < L] = -1
    return s


# ---------------------------------------------------------------- fair value gaps
def fvg_imm(o, h, l, c, gmin):
    """3-candle imbalance completed at bar i: bull if low[i] > high[i-2] by >= gmin. Continuation dir."""
    s = np.zeros(len(c), np.int8)
    h2 = np.r_[np.nan, np.nan, h[:-2]]; l2 = np.r_[np.nan, np.nan, l[:-2]]
    bull = (l - h2) >= gmin
    bear = (l2 - h) >= gmin
    s[bull] = 1; s[bear] = -1
    s[bull & bear] = 0
    return s


@njit(cache=True)
def _fvg_retrace(h, l, c, gmin, W, mode):
    """Track the most recent bull and bear FVG. On the first later bar (within W bars) that trades into
    the gap: mode 0 = enter in gap direction if the close holds the gap (close beyond the far edge
    not allowed), mode 1 = enter at the touch regardless of close; gap removed after first touch or if
    closed through. Returns gap direction (caller multiplies by -1 to fade)."""
    n = len(c)
    s = np.zeros(n, np.int8)
    bt = np.nan; bb = np.nan; bi = -1      # bull gap top (low[i]) / bottom (high[i-2]) / formed at
    st = np.nan; sb = np.nan; si = -1      # bear gap bottom (high[i]) / top (low[i-2])
    for i in range(2, n):
        # check existing gaps against bar i (formed strictly earlier)
        if bi >= 0:
            if i - bi > W:
                bi = -1
            elif l[i] <= bt:
                if mode == 1 or c[i] >= bb:
                    s[i] = 1
                bi = -1
        if si >= 0:
            if i - si > W:
                si = -1
            elif h[i] >= st:
                if mode == 1 or c[i] <= sb:
                    s[i] = -1 if s[i] == 0 else 0
                si = -1
        # new gaps completed at bar i
        if l[i] - h[i - 2] >= gmin:
            bt = l[i]; bb = h[i - 2]; bi = i
        if l[i - 2] - h[i] >= gmin:
            st = h[i]; sb = l[i - 2]; si = i
    return s


def fvg_retrace(o, h, l, c, gmin, W, mode=0):
    return _fvg_retrace(h, l, c, float(gmin), int(W), int(mode))


# ---------------------------------------------------------------- swings / BOS / retest / order blocks
@njit(cache=True)
def _structure(o, h, l, c, k, W, tol, kind):
    """Swing high at j = h[j] is the max of h[j-k..j+k] (strictly above the left side), CONFIRMED at j+k.
    kind 0: BOS signal at the first close beyond the last confirmed swing (continuation dir).
    kind 1: retest: after a BOS up of level Lv, first bar within W bars with low <= Lv+tol and close > Lv -> +1.
    kind 2: order block: after a BOS up, OB = last bearish candle between the swing low that preceded
            it and the BOS bar; first bar within W with low <= OB high and close >= OB low -> +1.
    kind 3: CHoCH: BOS against the direction of the previous BOS (continuation of the new direction).
    """
    n = len(c)
    s = np.zeros(n, np.int8)
    sh = np.nan; shi = -1; slv = np.nan; sli = -1
    trend = 0
    # pending retest / OB state
    up_lv = np.nan; up_i = -1; up_lo = np.nan
    dn_lv = np.nan; dn_i = -1; dn_hi = np.nan
    for i in range(n):
        # confirm swing at j = i - k
        j = i - k
        if j - k >= 0:
            isH = True; isL = True
            for t in range(j - k, j + k + 1):
                if t == j: continue
                if t < j:
                    if h[t] >= h[j]: isH = False
                    if l[t] <= l[j]: isL = False
                else:
                    if h[t] > h[j]: isH = False
                    if l[t] < l[j]: isL = False
            if isH: sh = h[j]; shi = j
            if isL: slv = l[j]; sli = j
        # pending retest / OB entries (set on earlier bars)
        if up_i >= 0:
            if i - up_i > W:
                up_i = -1
            elif kind == 1:
                if l[i] <= up_lv + tol:
                    if c[i] > up_lv: s[i] = 1
                    up_i = -1
            elif kind == 2:
                if l[i] <= up_lv:
                    if c[i] >= up_lo: s[i] = 1
                    up_i = -1
        if dn_i >= 0:
            if i - dn_i > W:
                dn_i = -1
            elif kind == 1:
                if h[i] >= dn_lv - tol:
                    if c[i] < dn_lv: s[i] = -1 if s[i] == 0 else 0
                    dn_i = -1
            elif kind == 2:
                if h[i] >= dn_lv:
                    if c[i] <= dn_hi: s[i] = -1 if s[i] == 0 else 0
                    dn_i = -1
        # BOS on this bar's close
        if shi >= 0 and c[i] > sh:
            if kind == 0: s[i] = 1
            elif kind == 3:
                if trend == -1: s[i] = 1
            elif kind == 1:
                up_lv = sh; up_i = i
            elif kind == 2:
                # last bearish candle between the swing high bar and i (search back to max(sli, shi-?))
                st = sli if (sli >= 0 and sli < i) else shi
                if st < i - 60: st = i - 60
                ob = -1
                for t in range(i - 1, st - 1, -1):
                    if c[t] < o[t]:
                        ob = t; break
                if ob >= 0:
                    up_lv = h[ob]; up_lo = l[ob]; up_i = i
            trend = 1
            shi = -1; sh = np.nan
        if sli >= 0 and c[i] < slv:
            if kind == 0: s[i] = -1 if s[i] == 0 else 0
            elif kind == 3:
                if trend == 1: s[i] = -1 if s[i] == 0 else 0
            elif kind == 1:
                dn_lv = slv; dn_i = i
            elif kind == 2:
                st = shi if (shi >= 0 and shi < i) else sli
                if st < i - 60: st = i - 60
                ob = -1
                for t in range(i - 1, st - 1, -1):
                    if c[t] > o[t]:
                        ob = t; break
                if ob >= 0:
                    dn_lv = l[ob]; dn_hi = h[ob]; dn_i = i
            trend = -1
            sli = -1; slv = np.nan
    return s


def structure(o, h, l, c, k, W=30, tol=0.0, kind=0):
    return _structure(o, h, l, c, int(k), int(W), float(tol), int(kind))


@njit(cache=True)
def _swing_sweep(o, h, l, c, k, maxage):
    """Sweep of the last CONFIRMED swing high/low (liquidity resting above/below a swing):
    wick beyond it and close back inside -> reversal. Swing removed once swept or closed through."""
    n = len(c)
    s = np.zeros(n, np.int8)
    sh = np.nan; shi = -1; slv = np.nan; sli = -1
    for i in range(n):
        j = i - k
        if j - k >= 0:
            isH = True; isL = True
            for t in range(j - k, j + k + 1):
                if t == j: continue
                if t < j:
                    if h[t] >= h[j]: isH = False
                    if l[t] <= l[j]: isL = False
                else:
                    if h[t] > h[j]: isH = False
                    if l[t] < l[j]: isL = False
            if isH: sh = h[j]; shi = j
            if isL: slv = l[j]; sli = j
        if shi >= 0 and i - shi > maxage: shi = -1
        if sli >= 0 and i - sli > maxage: sli = -1
        if shi >= 0 and shi < i - k and h[i] > sh:
            if c[i] < sh: s[i] = -1
            shi = -1
        if sli >= 0 and sli < i - k and l[i] < slv:
            if c[i] > slv: s[i] = 1 if s[i] == 0 else 0
            sli = -1
    return s


def swing_sweep(o, h, l, c, k, maxage=240):
    return _swing_sweep(o, h, l, c, int(k), int(maxage))


# ---------------------------------------------------------------- levels: round numbers, PDH/PDL, Asian range
def round_level(o, h, l, c, step, kind, e=0.0):
    """kind 'reject': bar pierces a handle by >= e but closes back on the side it came from (open side)
       -> trade away from the handle. kind 'break': close crosses a handle (prev close other side)
       -> continuation dir. kind 'near': close within e below (above) the next handle -> -1 (+1),
       i.e. expect rejection before touching."""
    n = len(c)
    s = np.zeros(n, np.int8)
    if kind == 'break':
        pc = np.r_[np.nan, c[:-1]]
        up = np.floor(c / step) > np.floor(pc / step)
        dn = np.floor(c / step) < np.floor(pc / step)
        s[up] = 1; s[dn] = -1
    elif kind == 'reject':
        Lh = np.floor(o / step) * step + step          # first handle above the open
        Ll = np.ceil(o / step) * step - step           # first handle below the open
        rh = (h >= Lh + e) & (c < Lh)
        rl = (l <= Ll - e) & (c > Ll)
        s[rh] = -1; s[rl] = 1; s[rh & rl] = 0
    elif kind == 'near':
        up = np.ceil(c / step) * step - c
        dn = c - np.floor(c / step) * step
        s[(up > 0) & (up <= e)] = -1
        s[(dn > 0) & (dn <= e)] = 1
        s[((up > 0) & (up <= e)) & ((dn > 0) & (dn <= e))] = 0
    return s


def day_levels(m1):
    """Previous server-day high/low for each M1 row (NaN on the first day)."""
    d = m1.index.normalize()
    g = m1.groupby(d)
    dh = g.high.max(); dl = g.low.min()
    pdh = dh.shift(1).reindex(d).values; pdl = dl.shift(1).reindex(d).values
    return pdh, pdl


def session_range(m1, start_tod, end_tod):
    """High/low of [start_tod, end_tod) server minutes of the same day, known only from end_tod on."""
    d = m1.index.normalize()
    tod = m1.tod.values
    inwin = (tod >= start_tod) & (tod < end_tod)
    x = m1[inwin]
    g = x.groupby(x.index.normalize())
    hi = g.high.max().reindex(d).values; lo = g.low.min().reindex(d).values
    known = tod >= end_tod
    hi = np.where(known, hi, np.nan); lo = np.where(known, lo, np.nan)
    return hi, lo


@njit(cache=True)
def _level_events(o, h, l, c, day, HI, LO, kind, e, maxn):
    """For levels HI/LO (NaN when unknown). kind 0 sweep-reversal: wick beyond by >= e, close back
    inside -> reversal. kind 1 break: first close beyond (continuation). Up to maxn events per level/day."""
    n = len(c)
    s = np.zeros(n, np.int8)
    cur = -1; nh = 0; nl = 0
    for i in range(1, n):
        if day[i] != cur:
            cur = day[i]; nh = 0; nl = 0
        if np.isnan(HI[i]) or np.isnan(LO[i]): continue
        if kind == 0:
            if nh < maxn and h[i] >= HI[i] + e and c[i] < HI[i]:
                s[i] = -1; nh += 1
            if nl < maxn and l[i] <= LO[i] - e and c[i] > LO[i]:
                s[i] = 1 if s[i] == 0 else 0; nl += 1
        else:
            if nh < maxn and c[i] > HI[i] and c[i - 1] <= HI[i]:
                s[i] = 1; nh += 1
            if nl < maxn and c[i] < LO[i] and c[i - 1] >= LO[i]:
                s[i] = -1 if s[i] == 0 else 0; nl += 1
    return s


def level_events(m1, day, HI, LO, kind, e=0.0, maxn=3):
    o, h, l, c = arrs(m1)
    return _level_events(o, h, l, c, day, np.asarray(HI, float), np.asarray(LO, float), int(kind), float(e), int(maxn))


# ---------------------------------------------------------------- edge measured on TRAIN only
def edge_train(m1, sig, spr, horizons=(1, 2, 3, 5, 10, 20)):
    """Average favourable move of the bid close over k bars per signal, TRAIN only, and split into
    the two TRAIN halves (before / after 2026-08-01) for stability. spr = per-bar spread array ($)."""
    sig = np.nan_to_num(np.asarray(sig, float))
    c = m1.close.values
    idx = m1.index
    out = {}
    tr = idx < SPLIT
    h1 = idx < pd.Timestamp('2026-08-01')
    nd = len(np.unique(idx[tr].date))
    m = (sig != 0) & tr
    out['n_day'] = m.sum() / nd
    out['spr'] = spr[m].mean() if m.any() else np.nan
    for k in horizons:
        f = np.full(len(c), np.nan)
        f[:-k] = (c[k:] - c[:-k])
        f = f * sig
        a = f[m]; a = a[~np.isnan(a)]
        out[f'mv{k}'] = a.mean() if len(a) else np.nan
        a1 = f[m & h1]; a1 = a1[~np.isnan(a1)]
        a2 = f[m & ~h1]; a2 = a2[~np.isnan(a2)]
        out[f'mv{k}_a'] = a1.mean() if len(a1) else np.nan
        out[f'mv{k}_b'] = a2.mean() if len(a2) else np.nan
        out[f'se{k}'] = a.std() / np.sqrt(max(len(a), 1)) if len(a) else np.nan
    return out
