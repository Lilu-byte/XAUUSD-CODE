"""Synthetic tick random walk -> M1 bid OHLC on real timestamps (copy of the audit's generator, kept local so nothing in
the shared audit folder is touched), with the v2 columns (tod, last_of_session) mlib.Harness needs.
Also a tick-exact grid-basket simulator (same rules as gridsim2) to calibrate the 4-vertex bar path model."""
import numpy as np, pandas as pd
from numba import njit, prange
from mysim2 import Harness, END_TOD, LAST_ENTRY_TOD, FIRST_ENTRY_TOD


@njit(parallel=True, cache=True)
def gen_steps(K_arr, offs, p, seed):
    n = len(K_arr)
    steps = np.empty(offs[-1], np.int8)
    for j in prange(n):
        np.random.seed(seed * 1000003 + j)
        a = offs[j]
        for t in range(K_arr[j]):
            steps[a + t] = 1 if np.random.random() < p else -1
    return steps


@njit(cache=True)
def build_ohlc(steps, offs, start_cents):
    n = len(offs) - 1
    o = np.empty(n, np.int64); h = np.empty(n, np.int64); l = np.empty(n, np.int64); c = np.empty(n, np.int64)
    x = start_cents
    for j in range(n):
        o[j] = x; hi = x; lo = x
        for t in range(offs[j], offs[j + 1]):
            x += steps[t]
            if x > hi: hi = x
            if x < lo: lo = x
        h[j] = hi; l[j] = lo; c[j] = x
    return o, h, l, c


def synth_harness(real_m1, K, p=0.5, seed=1, spread_usd=0.15):
    n = len(real_m1)
    K_arr = np.full(n, K, np.int64)
    offs = np.zeros(n + 1, np.int64); offs[1:] = np.cumsum(K_arr)
    steps = gen_steps(K_arr, offs, p, seed)
    o, h, l, c = build_ohlc(steps, offs, 400000)
    m = pd.DataFrame({'open': o / 100.0, 'high': h / 100.0, 'low': l / 100.0, 'close': c / 100.0,
                      'tick_volume': float(K), 'spread': spread_usd * 100}, index=real_m1.index)
    m['spread_usd'] = spread_usd
    m['tod'] = real_m1.tod.values
    m['last_of_session'] = real_m1.last_of_session.values
    return Harness(m), steps, offs, o


@njit(cache=True)
def grid_tick(steps, offs, oc, spr, tod, day, last, dirsig, step, maxlev, btp, bsl, tmax):
    """Tick-exact grid basket: same rules as gridsim2._grid but every $0.01 tick is visited; levels fill at the level
    price (continuous convention). Returns per-day pnl, positions per day and basket pnls."""
    n = len(oc); nd = day[-1] + 1
    dpnl = np.zeros(nd); dpos = np.zeros(nd); bp = np.zeros(n); nb = 0
    nlev = 0; d = 0; E = 0.0; lastp = 0.0; t0 = 0
    for i in range(n):
        a = spr[i]
        x = oc[i]
        for t in range(offs[i], offs[i + 1] + 1):
            if t > offs[i]: x += steps[t - 1]
            if nlev == 0: continue
            b = x / 100.0
            for _ in range(maxlev + 2):
                if nlev == 0: break
                if d == 1:
                    lt = (E + btp) / nlev; la = lastp - step - a if nlev < maxlev else -1e18
                    ls = (E - bsl) / nlev if bsl > 0 else -1e18
                    if b >= lt - 1e-9:
                        v = nlev * lt - E; dpnl[day[t0]] += v; bp[nb] = v; nb += 1; nlev = 0; break
                    if bsl > 0 and b <= ls + 1e-9:
                        v = nlev * ls - E; dpnl[day[t0]] += v; bp[nb] = v; nb += 1; nlev = 0; break
                    if b <= la + 1e-9:
                        e = la + a; nlev += 1; E += e; lastp = e; dpos[day[i]] += 1
                    else: break
                else:
                    lt = (E - btp) / nlev - a; la = lastp + step if nlev < maxlev else 1e18
                    ls = (E + bsl) / nlev - a if bsl > 0 else 1e18
                    if b <= lt + 1e-9:
                        v = E - nlev * (lt + a); dpnl[day[t0]] += v; bp[nb] = v; nb += 1; nlev = 0; break
                    if bsl > 0 and b >= ls - 1e-9:
                        v = E - nlev * (ls + a); dpnl[day[t0]] += v; bp[nb] = v; nb += 1; nlev = 0; break
                    if b >= la - 1e-9:
                        e = la; nlev += 1; E += e; lastp = e; dpos[day[i]] += 1
                    else: break
        cb = x / 100.0
        if nlev > 0 and ((tmax > 0 and i - t0 >= tmax) or tod[i] >= END_TOD or last[i] or i == n - 1):
            v = (nlev * cb - E) if d == 1 else (E - nlev * (cb + a)); dpnl[day[t0]] += v; bp[nb] = v; nb += 1; nlev = 0
        if nlev == 0 and dirsig[i] != 0 and tod[i] <= LAST_ENTRY_TOD and tod[i] >= FIRST_ENTRY_TOD and not last[i] and i < n - 1:
            d = dirsig[i]; e = cb + a if d == 1 else cb
            nlev = 1; E = e; lastp = e; t0 = i; dpos[day[i]] += 1
    return dpnl, dpos, bp[:nb]
