"""Round-2 helpers for the ML family, written for mlib v2 (session force-close, entries 01:05-22:29,
hour-median spread imputation). Re-uses feat.build (feature code) and adds:
  tradeable2(m1)      entry mask identical to mlib v2's entry rule
  bracket_pnl2(...)   per-bar P&L of one long / one short opened at close i, exactly the v2 _sim exit logic
  BRK / bracket_arrays(H)   P&L arrays for a grid of (tp, sl, timeout) brackets (FAIR fill, base spread)
  folds               3-fold expanding walk-forward inside TRAIN (OOS = Jul20..Aug31, 31 days)
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
import numpy as np, pandas as pd
from numba import njit
from mlib import (Harness, load_m1, load, SPLIT, END_TOD, LAST_ENTRY_TOD, FIRST_ENTRY_TOD, FILL, summarize,
                  edge, random_like)

FAM = '/mnt/project-files/xauusd-microscalp/families/ml-model/'
B = [pd.Timestamp(x) for x in ('2026-07-20', '2026-08-03', '2026-08-17', '2026-09-01')]
TP_GRID = (0.1, 0.2, 0.3, 0.5, 0.75, 1.0)
SL_GRID = (0.3, 0.5, 1.0, 2.0, 3.0, 5.0)
TO_GRID = (2, 3, 5, 10, 20, 30)
BRK = [(tp, sl, to) for tp in TP_GRID for sl in SL_GRID for to in TO_GRID]


def tradeable2(m1):
    t = m1.tod.values
    return (t >= FIRST_ENTRY_TOD) & (t <= LAST_ENTRY_TOD) & ~m1.last_of_session.values & (np.arange(len(m1)) < len(m1) - 1)


@njit(cache=True)
def bracket_pnl2(o, h, l, c, spr, tod, day, last, tp, sl, timeout, fill):
    """P&L of a long (L) and a short (S) opened at the close of every bar i, same rules as mlib v2 _sim."""
    n = len(c); L = np.full(n, np.nan); S = np.full(n, np.nan); NB = np.full(n, -1, np.int64)
    for i in range(n - 1):
        for s in (1, -1):
            e = c[i] + spr[i] if s == 1 else c[i]
            pnl = np.nan; jj = -1
            for j in range(i + 1, n):
                a = spr[j]
                stale = (j - i >= timeout) or (tod[j] >= END_TOD) or last[j] or (j == n - 1) or (day[j] != day[i])
                ex = False; px = 0.0
                if s == 1:
                    tpp = e + tp; slp = e - sl
                    if day[j] != day[i]: px = o[j]; ex = True
                    elif o[j] <= slp or o[j] >= tpp: px = o[j]; ex = True
                    else:
                        ht = h[j] >= tpp; hs = l[j] <= slp
                        if ht and hs:
                            if fill == 0: px = slp
                            elif fill == 3: px = tpp
                            elif fill == 2: px = slp if c[j] > o[j] else tpp
                            else:
                                q = (o[j] - slp) / (tpp - slp); px = q * tpp + (1 - q) * slp
                            ex = True
                        elif ht: px = tpp; ex = True
                        elif hs: px = slp; ex = True
                    if not ex and stale: px = c[j]; ex = True
                    if ex: pnl = px - e
                else:
                    tpp = e - tp; slp = e + sl
                    ao = o[j] + a
                    if day[j] != day[i]: px = ao; ex = True
                    elif ao >= slp or ao <= tpp: px = ao; ex = True
                    else:
                        ht = l[j] + a <= tpp; hs = h[j] + a >= slp
                        if ht and hs:
                            if fill == 0: px = slp
                            elif fill == 3: px = tpp
                            elif fill == 2: px = tpp if c[j] > o[j] else slp
                            else:
                                q = (slp - ao) / (slp - tpp); px = q * tpp + (1 - q) * slp
                            ex = True
                        elif ht: px = tpp; ex = True
                        elif hs: px = slp; ex = True
                    if not ex and stale: px = c[j] + a; ex = True
                    if ex: pnl = e - px
                if ex:
                    jj = j; break
            if s == 1:
                L[i] = pnl; NB[i] = jj - i
            else:
                S[i] = pnl
    return L, S, NB


def bracket_arrays(H, spread='base', fill='FAIR', brk=BRK):
    """dict (tp, sl, to) -> (L, S) float32 arrays, NaN where an entry is not allowed."""
    ok = tradeable2(H.m1)
    out = {}
    for tp, sl, to in brk:
        L, S, _ = bracket_pnl2(H.o, H.h, H.l, H.c, H._spr[spread], H.tod, H.day, H.last, float(tp), float(sl), int(to), FILL[fill])
        L[~ok] = np.nan; S[~ok] = np.nan
        out[(tp, sl, to)] = (L.astype(np.float32), S.astype(np.float32))
    return out


def roll_thr(s, q, window=3960, min_periods=500):
    """(1-q) quantile of |s| over the previous `window` scored rows (current row excluded): known live."""
    a = pd.Series(np.abs(s))
    return a.shift(1).rolling(window, min_periods=min_periods).quantile(1 - q).values


def roll_center(s, window=3960, min_periods=500):
    """Score minus its trailing median over the previous `window` rows (removes a persistent long/short bias)."""
    a = pd.Series(s)
    return (a - a.shift(1).rolling(window, min_periods=min_periods).median()).values


def signal_q(s, q, center=False, window=3960, min_periods=500):
    """+1/-1 where |score| is in the trailing top-q of the previous `window` scored rows. Rows with a NaN score (e.g. an
    M5 model scored only at M5 closes) are skipped and the window/min_periods are scaled to the scored share."""
    s = np.asarray(s, float)
    have = ~np.isnan(s)
    if not have.all():
        out = np.zeros(len(s), np.int64); sh = have.mean()
        out[have] = signal_q(s[have], q, center, max(int(window * sh), 50), max(int(min_periods * sh), 20))
        return out
    if center: s = roll_center(s, window, min_periods)
    thr = roll_thr(s, q, window, min_periods)
    ok = (np.abs(s) >= thr) & ~np.isnan(thr)
    return np.where(ok, np.sign(s), 0).astype(np.int64)


def fold_of(T):
    """0 = before Jul20 (only ever used for fitting), 1..3 = walk-forward validation folds, 4 = TEST."""
    return np.searchsorted(np.array(B, dtype='datetime64[ns]'), T.values, side='right')
