"""Copy of mlib._sim with ONE change: entry at the next bar open (the EA's first tick) instead of the signal bar close."""
import numpy as np
from numba import njit
END_TOD = 22 * 60 + 58
LAST_ENTRY_TOD = 22 * 60 + 29
FIRST_ENTRY_TOD = 1 * 60 + 5


@njit
def _sim_next(o, h, l, c, spr, tod, day, last, sig, tp, sl, timeout, max_open, fill, day_target, day_loss, cooldown, spr_next=True):
    n = len(c)
    nd = day[-1] + 1
    dpnl = np.zeros(nd); dtr = np.zeros(nd)
    t_in = np.empty(n, np.int64); t_out = np.empty(n, np.int64); t_pnl = np.empty(n); t_dir = np.empty(n, np.int64)
    nt = 0
    pdir = np.zeros(max_open, np.int64); pent = np.zeros(max_open); pidx = np.full(max_open, -1, np.int64)
    pact = np.zeros(max_open, np.bool_); pslot = np.zeros(max_open, np.int64)
    cur = -1; dsum = 0.0; halted = False; last_entry = -1000000
    for i in range(n):
        if day[i] != cur:
            cur = day[i]; dsum = 0.0; halted = False
        # 1) exits on bar i for positions opened on earlier bars
        for k in range(max_open):
            if not pact[k] or pidx[k] >= i: continue
            e = pent[k]; s = pdir[k]; ex = False; px = 0.0
            a = spr[i]
            stale = (i - pidx[k] >= timeout) or (tod[i] >= END_TOD) or last[i] or (i == n - 1) or (day[i] != day[pidx[k]])
            if s == 1:
                tpp = e + tp; slp = e - sl
                if day[i] != day[pidx[k]]: px = o[i]; ex = True
                elif o[i] <= slp or o[i] >= tpp: px = o[i]; ex = True
                else:
                    hit_t = h[i] >= tpp; hit_s = l[i] <= slp
                    if hit_t and hit_s:
                        if fill == 0: px = slp
                        elif fill == 3: px = tpp
                        elif fill == 2:
                            px = slp if c[i] > o[i] else tpp
                        else:
                            q = (o[i] - slp) / (tpp - slp); px = q * tpp + (1 - q) * slp
                        ex = True
                    elif hit_t: px = tpp; ex = True
                    elif hit_s: px = slp; ex = True
                if not ex and stale: px = c[i]; ex = True
                pnl = px - e
            else:
                tpp = e - tp; slp = e + sl
                ao = o[i] + a; ah = h[i] + a; al = l[i] + a; ac = c[i] + a
                if day[i] != day[pidx[k]]: px = ao; ex = True
                elif ao >= slp or ao <= tpp: px = ao; ex = True
                else:
                    hit_t = al <= tpp; hit_s = ah >= slp
                    if hit_t and hit_s:
                        if fill == 0: px = slp
                        elif fill == 3: px = tpp
                        elif fill == 2:
                            px = tpp if c[i] > o[i] else slp
                        else:
                            q = (slp - ao) / (slp - tpp); px = q * tpp + (1 - q) * slp
                        ex = True
                    elif hit_t: px = tpp; ex = True
                    elif hit_s: px = slp; ex = True
                if not ex and stale: px = ac; ex = True
                pnl = e - px
            if ex:
                pact[k] = False
                j = pslot[k]
                t_out[j] = i; t_pnl[j] = pnl
                dpnl[day[pidx[k]]] += pnl
                if day[pidx[k]] == cur:
                    dsum += pnl
                    if (day_target > 0 and dsum >= day_target) or (day_loss > 0 and dsum <= -day_loss): halted = True
        # 2) entry at the close of bar i
        s = sig[i]
        if s != 0 and not halted and tod[i] <= LAST_ENTRY_TOD and tod[i] >= FIRST_ENTRY_TOD and not last[i] and i < n - 1 and i - last_entry >= cooldown:
            for k in range(max_open):
                if not pact[k]:
                    pact[k] = True; pdir[k] = s; pidx[k] = i; pslot[k] = nt
                    pent[k] = o[i + 1] + (spr[i + 1] if spr_next else spr[i]) if s == 1 else o[i + 1]   # EA: first tick of the next bar
                    t_in[nt] = i; t_dir[nt] = s; t_out[nt] = -1; t_pnl[nt] = 0.0
                    nt += 1; dtr[day[i]] += 1; last_entry = i
                    break
    return dpnl, dtr, t_in[:nt], t_out[:nt], t_pnl[:nt], t_dir[:nt]


