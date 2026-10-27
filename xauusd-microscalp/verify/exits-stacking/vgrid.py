"""Independent re-implementation of the averaging-down grid basket (verifier; does NOT import the colleague's code).

Rule (from the claim text):
  * when flat, at the close of bar i where sig[i] != 0 (entry window FIRST_ENTRY_TOD..LAST_ENTRY_TOD, not the last bar of a
    session, not the last bar of the data) open 1 x 0.01 lot in direction sig[i]  (long at ask = bid close + spread, short at bid)
  * while open: every time the entry-side price moves `step` $ against the LAST entry, add one more 0.01 lot (max `maxlev`)
      long : add when ask <= last_entry - step  (i.e. bid <= last - step - spread)  -> new entry at that ask
      short: add when bid >= last_entry + step                                      -> new entry at that bid
  * close ALL when combined floating P&L (long: n*bid - sum(ask entries); short: sum(bid entries) - n*ask) >= btp
  * optional basket stop (bsl>0) / time limit (tmax>0); always force-close at the close of the session's last bar / END_TOD
In-bar path: vertices prev_close -> (jump) open -> ext1 -> ext2 -> close. Monotone segments, events filled exactly at their
level; a jump (gap) fills at the open. One basket at a time; 0.01 lot = $1 per $1.
Path modes: 0 FAIR4 (P(high first) = mean of (o-l)/(h-l) and (h-c)/(h-l)), 1 OHLC (bull O-L-H-C, else O-H-L-C),
            2 ADV (extreme against the open basket first), 3 FAIRO (P(high first) = (o-l)/(h-l)), 4 FAV (favourable first)
gap_multi: if True a gap through k add levels adds k positions at the open (pending-limit style); else 1 (market style).
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _flt(n, d, E, bid, a):
    if n == 0:
        return 0.0
    if d == 1:
        return n * bid - E
    return E - n * (bid + a)


@njit(cache=True)
def grid_core(o, h, l, c, spr, tod, day, last, sig, step, maxlev, btp, bsl, tmax, path, seed,
              first_tod, last_tod, end_tod, gap_multi):
    np.random.seed(seed)
    N = len(c); ND = day[-1] + 1
    dpnl = np.zeros(ND); dpos = np.zeros(ND); dbsk = np.zeros(ND)
    # basket log
    b_start = np.zeros(N, np.int64); b_end = np.zeros(N, np.int64); b_dir = np.zeros(N, np.int64)
    b_lev = np.zeros(N, np.int64); b_pnl = np.zeros(N); b_why = np.zeros(N, np.int64); b_mae = np.zeros(N)
    eq_low = np.zeros(N)       # lowest (realised + floating) equity seen inside bar i
    lev_hi = np.zeros(N, np.int64)
    nb = 0
    n = 0; d = 0; E = 0.0; lastp = 0.0; t0 = 0; mae = 0.0
    realised = 0.0
    vx = np.zeros(4)
    for i in range(N):
        a = spr[i]
        lowest = realised + _flt(n, d, E, c[i - 1] if i > 0 else o[i], a)
        levmax = n
        # path
        if h[i] > l[i]:
            if path == 0:
                pu = 0.5 * ((o[i] - l[i]) + (h[i] - c[i])) / (h[i] - l[i])
                up = np.random.random() < pu
            elif path == 1:
                up = not (c[i] > o[i])
            elif path == 2:
                up = (d == -1)          # short basket: high first hurts; long basket (or flat): low first
            elif path == 3:
                up = np.random.random() < (o[i] - l[i]) / (h[i] - l[i])
            else:
                up = (d == 1)
        else:
            up = True
        vx[0] = o[i]
        if up:
            vx[1] = h[i]; vx[2] = l[i]
        else:
            vx[1] = l[i]; vx[2] = h[i]
        vx[3] = c[i]
        p = c[i - 1] if i > 0 else o[i]
        for v in range(4):
            q = vx[v]
            jump = (v == 0)
            # walk segment p -> q
            guard = 0
            while n > 0 and guard < 1000:
                guard += 1
                if d == 1:
                    tgt = (E + btp) / n                         # bid level where target is reached
                    if q >= p:
                        if q >= tgt - 1e-12:
                            fx = q if jump else max(tgt, p)
                            val = n * fx - E
                            dpnl[day[t0]] += val; realised += val
                            b_start[nb] = t0; b_end[nb] = i; b_dir[nb] = d; b_lev[nb] = n; b_pnl[nb] = val; b_why[nb] = 0; b_mae[nb] = mae; nb += 1
                            n = 0; E = 0.0
                        break
                    # moving down
                    addl = (lastp - step - a) if n < maxlev else -1e18
                    stpl = ((E - bsl) / n) if bsl > 0 else -1e18
                    lv = max(addl, stpl)
                    if lv < q - 1e-12:
                        break
                    fx = q if jump else min(lv, p)
                    if stpl >= addl:
                        val = n * fx - E
                        dpnl[day[t0]] += val; realised += val
                        b_start[nb] = t0; b_end[nb] = i; b_dir[nb] = d; b_lev[nb] = n; b_pnl[nb] = val; b_why[nb] = 1; b_mae[nb] = mae; nb += 1
                        n = 0; E = 0.0
                        break
                    e = fx + a
                    n += 1; E += e; lastp = e; dpos[day[i]] += 1
                    if n > levmax: levmax = n
                    if jump and not gap_multi:
                        break
                    p = fx
                else:
                    tgt = (E - btp) / n - a                     # bid level where target is reached
                    if q <= p:
                        if q <= tgt + 1e-12:
                            fx = q if jump else min(tgt, p)
                            val = E - n * (fx + a)
                            dpnl[day[t0]] += val; realised += val
                            b_start[nb] = t0; b_end[nb] = i; b_dir[nb] = d; b_lev[nb] = n; b_pnl[nb] = val; b_why[nb] = 0; b_mae[nb] = mae; nb += 1
                            n = 0; E = 0.0
                        break
                    addl = (lastp + step) if n < maxlev else 1e18
                    stpl = ((E + bsl) / n - a) if bsl > 0 else 1e18
                    lv = min(addl, stpl)
                    if lv > q + 1e-12:
                        break
                    fx = q if jump else max(lv, p)
                    if stpl <= addl:
                        val = E - n * (fx + a)
                        dpnl[day[t0]] += val; realised += val
                        b_start[nb] = t0; b_end[nb] = i; b_dir[nb] = d; b_lev[nb] = n; b_pnl[nb] = val; b_why[nb] = 1; b_mae[nb] = mae; nb += 1
                        n = 0; E = 0.0
                        break
                    e = fx
                    n += 1; E += e; lastp = e; dpos[day[i]] += 1
                    if n > levmax: levmax = n
                    if jump and not gap_multi:
                        break
                    p = fx
            p = q
            f = _flt(n, d, E, q, a)
            if n > 0 and f < mae: mae = f
            if realised + f < lowest: lowest = realised + f
        # forced close (time limit / session end / end of data)
        if n > 0 and ((tmax > 0 and i - t0 >= tmax) or tod[i] >= end_tod or last[i] or i == N - 1):
            val = _flt(n, d, E, c[i], a)
            dpnl[day[t0]] += val; realised += val
            b_start[nb] = t0; b_end[nb] = i; b_dir[nb] = d; b_lev[nb] = n; b_pnl[nb] = val; b_why[nb] = 2; b_mae[nb] = mae; nb += 1
            n = 0; E = 0.0
        # new basket at the close of bar i
        if n == 0 and sig[i] != 0 and tod[i] >= first_tod and tod[i] <= last_tod and not last[i] and i < N - 1:
            d = sig[i]; n = 1
            E = c[i] + a if d == 1 else c[i]
            lastp = E; t0 = i; mae = _flt(n, d, E, c[i], a)
            dpos[day[i]] += 1; dbsk[day[i]] += 1
            if levmax < 1: levmax = 1
            f = _flt(n, d, E, c[i], a)
            if realised + f < lowest: lowest = realised + f
        eq_low[i] = lowest
        lev_hi[i] = levmax
    return (dpnl, dpos, dbsk, eq_low, lev_hi, b_start[:nb], b_end[:nb], b_dir[:nb], b_lev[:nb], b_pnl[:nb], b_why[:nb], b_mae[:nb])
