"""Synthetic tick-level random walk -> M1 bid OHLC, plus a tick-exact 'truth' simulator that mirrors the
harness's entry/exit rules (entry at signal-bar close, exits on later bars, timeout at bar close, day change
exit at the next session's open, max_open slots) but resolves TP/SL with the real tick path.

Price lattice: $0.01 steps; each M1 bar has K steps (sigma per minute = 0.01*sqrt(K)).
Up-step probability p (0.5 = martingale; p > 0.5 = known upward drift)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
from numba import njit, prange
import mlib


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


EPS = 1e-7   # a tick exactly at a level triggers it (MT5: bid >= TP / bid <= SL); avoids float-tie artefacts


@njit(cache=True)
def truth_sim(steps, offs, oc, cc, spr, day, sig, tp, sl, timeout, max_open, at_level):
    """Tick-exact outcome of the same rules. Fills at the first tick that is at/through a level, at that tick's
    price (exact martingale accounting). Ticks within 1e-7 of a level count as touching it."""
    n = len(oc)
    t_in = np.empty(n, np.int64); t_out = np.empty(n, np.int64); t_pnl = np.empty(n); t_dir = np.empty(n, np.int64)
    t_ticks = np.empty(n, np.int64); t_lvl = np.empty(n)
    nt = 0
    pdir = np.zeros(max_open, np.int64); pent = np.zeros(max_open); pidx = np.full(max_open, -1, np.int64)
    pact = np.zeros(max_open, np.bool_); pslot = np.zeros(max_open, np.int64); ptk = np.zeros(max_open, np.int64)
    for i in range(n):
        for k in range(max_open):
            if not pact[k] or pidx[k] >= i: continue
            e = pent[k]; s = pdir[k]; a = spr[i]
            stale = (i - pidx[k] >= timeout) or (i == n - 1)
            ex = False; px = 0.0; lvl = 0.0
            if day[i] != day[pidx[k]]:
                px = oc[i] / 100.0 + (0.0 if s == 1 else a); ex = True
            else:
                if s == 1:
                    tpp = e + tp; slp = e - sl
                else:
                    tpp = e - tp; slp = e + sl
                x = oc[i]
                t = offs[i]
                while True:
                    b = x / 100.0
                    q = b if s == 1 else b + a
                    first = t == offs[i]
                    if s == 1:
                        if q >= tpp - EPS: px = q if (first or not at_level) else tpp; lvl = tpp; ex = True; break
                        if q <= slp + EPS: px = q if (first or not at_level) else slp; lvl = slp; ex = True; break
                    else:
                        if q <= tpp + EPS: px = q if (first or not at_level) else tpp; lvl = tpp; ex = True; break
                        if q >= slp - EPS: px = q if (first or not at_level) else slp; lvl = slp; ex = True; break
                    if t >= offs[i + 1]: break
                    x += steps[t]; t += 1
                    ptk[k] += 1
                if not ex and stale:
                    px = cc[i] / 100.0 + (0.0 if s == 1 else a); ex = True
            if ex:
                pnl = px - e if s == 1 else e - px
                pact[k] = False; j = pslot[k]
                t_out[j] = i; t_pnl[j] = pnl; t_ticks[j] = ptk[k]; t_lvl[j] = (lvl - e) * s if lvl != 0.0 else np.nan
        s = sig[i]
        if s != 0 and i < n - 1:
            for k in range(max_open):
                if not pact[k]:
                    pact[k] = True; pdir[k] = s; pidx[k] = i; pslot[k] = nt; ptk[k] = 0
                    pent[k] = cc[i] / 100.0 + spr[i] if s == 1 else cc[i] / 100.0
                    t_in[nt] = i; t_dir[nt] = s; t_out[nt] = -1; t_pnl[nt] = 0.0
                    nt += 1
                    break
    return t_in[:nt], t_out[:nt], t_pnl[:nt], t_dir[:nt], t_ticks[:nt], t_lvl[:nt]


class Synth:
    def __init__(self, real_m1, K, p=0.5, seed=1, spread_pts=20):
        n = len(real_m1)
        K_arr = np.full(n, K, np.int64) if np.isscalar(K) else np.asarray(K, np.int64)
        offs = np.zeros(n + 1, np.int64); offs[1:] = np.cumsum(K_arr)
        self.steps = gen_steps(K_arr, offs, p, seed)
        self.offs = offs
        o, h, l, c = build_ohlc(self.steps, offs, 400000)
        self.oc, self.cc = o, c
        m = pd.DataFrame({'open': o / 100.0, 'high': h / 100.0, 'low': l / 100.0, 'close': c / 100.0,
                          'tick_volume': K_arr.astype(float), 'spread': float(spread_pts)}, index=real_m1.index)
        m['spread_usd'] = m.spread * 0.01
        m['tod'] = m.index.hour * 60 + m.index.minute
        self.m1 = m
        self.H = mlib.Harness(m)
        self.K_arr = K_arr

    def truth(self, sig, tp, sl, timeout=10, max_open=1, at_level=False):
        """at_level=False: fill at the crossing tick (exact martingale). True: fill exactly at the level (continuous-
        price convention, same as the harness), so harness and truth differ only on bars where both levels are hit."""
        sig = np.nan_to_num(np.asarray(sig, float)).astype(np.int64)
        ti, to, tpn, tdr, ttk, tlv = truth_sim(self.steps, self.offs, self.oc, self.cc, self.H._spr['bar'], self.H.day,
                                               sig, float(tp), float(sl), int(timeout), int(max_open), bool(at_level))
        return pd.DataFrame({'i_in': ti, 'i_out': to, 'pnl': tpn, 'dir': tdr, 'ticks': ttk, 'lvl': tlv})
