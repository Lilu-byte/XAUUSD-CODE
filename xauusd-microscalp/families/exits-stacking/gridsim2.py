"""Averaging-down / grid basket simulator, mlib v2 conventions (rewritten 2026-10-14; v1 version in v1_old/).
Bid candles; longs enter at ask = bid + spread and exit at bid; shorts enter at bid and exit at ask.

Basket rules: when flat, at the close of bar i with dirsig[i] != 0 (entry window 01:05-22:29 server, not the last bar
of a session), open 1 position (0.01 lot) in that direction. While the basket is open, every time the entry-side
price moves `step` $ against the LAST entry, add one more 0.01 position (up to `maxlev` positions).
Close ALL positions when the basket's combined floating profit reaches `btp` $, or falls to -`bsl` $ (0 = no
basket stop), or `tmax` bars after the first entry (0 = no limit), or at the close of the last bar of the session
(22:58 server or earlier: the v2 force-close). A new basket can only start at a bar close.

Inside each M1 bar the price path is one of:
'FAIR' (= 'FAIR4', default): 4-vertex path O -> first extreme -> second extreme -> C, P(high first) = mean of
         (o-l)/(h-l) and (h-c)/(h-l) (gambler's-ruin odds from the open and, time-reversed, from the close).
         Calibrated in gridtest2.py against a tick-exact grid simulator on synthetic random walks: per-position
         error -4c..+6c, on average ~1-2c optimistic (no intra-bar wiggles).
'BRIDGE': Brownian bridge O -> C with `nsub` steps, excursions rescaled to touch H and L. Rejected: at nsub=30 it is
         3-11c/position optimistic vs tick truth (it revisits the extremes too often); at nsub=200 it is no better
         than FAIR4. Kept for reference only.
'OHLC' : MT5 1-minute-OHLC path (bull bar O-L-H-C, bear/flat O-H-L-C).  'ADV': worst extreme order for the basket.
Levels crossed by the gap from the previous close to the open fill at the open; levels crossed inside a segment
fill exactly at the level. Equity (realised + floating) and open positions are tracked at every path vertex.
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
from numba import njit
from mlib import SPLIT, END_TOD, LAST_ENTRY_TOD, FIRST_ENTRY_TOD

PATH = {'FAIR4': 0, 'FAIR': 0, 'OHLC': 1, 'ADV': 2, 'BRIDGE': 3}
# state vector: 0 nlev, 1 dir, 2 E (sum of entry prices), 3 last entry price, 4 t0 (start bar), 5 mae, 6 cum realised


@njit(cache=True)
def _close_b(st, val, i, why, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb):
    t0 = int(st[4])
    dpnl[day[t0]] += val
    b_pnl[nb] = val; b_lev[nb] = int(st[0]); b_dur[nb] = i - t0; b_why[nb] = why; b_start[nb] = t0; b_mae[nb] = st[5]
    st[6] += val; st[0] = 0; st[2] = 0.0
    return nb + 1


@njit(cache=True)
def _seg(st, p, q, jump, a, step, maxlev, btp, bsl, i, day, dpnl, dpos, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb):
    """Move the bid from p to q (straight segment, or a jump if `jump`), processing basket events in price order.
    Returns the new basket count."""
    for _ in range(maxlev + 3):
        nlev = st[0]
        if nlev == 0: break
        d = st[1]; E = st[2]; last = st[3]
        if d == 1:
            lt = (E + btp) / nlev
            la = last - step - a if nlev < maxlev else -1e18
            ls = (E - bsl) / nlev if bsl > 0 else -1e18
            if q >= p:
                if lt <= q + 1e-12:
                    fill = q if jump else max(lt, p)
                    nb = _close_b(st, nlev * fill - E, i, 0, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
                break
            lv = max(la, ls)
            if lv < -1e17 or lv < q - 1e-12: break
            fill = q if jump else min(lv, p)
            if ls >= la:
                nb = _close_b(st, nlev * fill - E, i, 1, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
                break
            e = fill + a; st[0] = nlev + 1; st[2] = E + e; st[3] = e; dpos[day[i]] += 1
            if jump: break
            p = fill
        else:
            lt = (E - btp) / nlev - a
            la = last + step if nlev < maxlev else 1e18
            ls = (E + bsl) / nlev - a if bsl > 0 else 1e18
            if q <= p:
                if lt >= q - 1e-12:
                    fill = q if jump else min(lt, p)
                    nb = _close_b(st, E - nlev * (fill + a), i, 0, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
                break
            lv = min(la, ls)
            if lv > 1e17 or lv > q + 1e-12: break
            fill = q if jump else max(lv, p)
            if ls <= la:
                nb = _close_b(st, E - nlev * (fill + a), i, 1, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
                break
            e = fill; st[0] = nlev + 1; st[2] = E + e; st[3] = e; dpos[day[i]] += 1
            if jump: break
            p = fill
    return nb


@njit(cache=True)
def _bridge(o, h, l, c, nsub, px, z):
    """Random path O -> C with nsub steps touching exactly H and L (Brownian bridge, excursions rescaled)."""
    if h <= l:
        px[0] = o; px[1] = c
        return 2
    z[0] = 0.0
    for k in range(1, nsub + 1):
        z[k] = z[k - 1] + np.random.normal()
    zN = z[nsub]
    for k in range(nsub + 1):
        z[k] = z[k] - zN * k / nsub
    au = 1e18; ad = 1e18; kmax = 1; kmin = 1; dmx = -1e18; dmn = 1e18
    for k in range(1, nsub):
        ln = o + (c - o) * k / nsub
        if z[k] > 0 and (h - ln) / z[k] < au: au = (h - ln) / z[k]
        if z[k] < 0 and (ln - l) / (-z[k]) < ad: ad = (ln - l) / (-z[k])
        if z[k] > dmx: dmx = z[k]; kmax = k
        if z[k] < dmn: dmn = z[k]; kmin = k
    if au > 1e17: au = 0.0
    if ad > 1e17: ad = 0.0
    px[0] = o
    for k in range(1, nsub):
        ln = o + (c - o) * k / nsub
        px[k] = ln + (au * z[k] if z[k] > 0 else ad * z[k])
    px[nsub] = c
    # if no excursion reached an extreme (all bridge points on one side), pin the extreme at the closest point
    hi = max(o, c); lo = min(o, c)
    for k in range(1, nsub):
        if px[k] > hi: hi = px[k]
        if px[k] < lo: lo = px[k]
    if hi < h - 1e-9:
        px[kmax] = h
    if lo > l + 1e-9:
        px[kmin if kmin != kmax else (kmax % (nsub - 1)) + 1] = l
    return nsub + 1


@njit(cache=True)
def _float(st, x, a):
    if st[0] == 0: return 0.0
    return (st[0] * x - st[2]) if st[1] == 1 else (st[2] - st[0] * (x + a))


@njit(cache=True)
def _grid(o, h, l, c, spr, tod, day, last, dirsig, step, maxlev, btp, bsl, tmax, path, seed, nsub):
    """why: 0 = basket target, 1 = basket stop, 2 = timeout / session end / end of data."""
    np.random.seed(seed)
    n = len(c); nd = day[-1] + 1
    dpnl = np.zeros(nd); dbask = np.zeros(nd); dpos = np.zeros(nd); dmin = np.zeros(nd)
    eq_min = np.zeros(n); lev_max = np.zeros(n, np.int64)
    b_pnl = np.zeros(n); b_lev = np.zeros(n, np.int64); b_dur = np.zeros(n, np.int64); b_why = np.zeros(n, np.int64)
    b_start = np.zeros(n, np.int64); b_mae = np.zeros(n)
    nb = 0
    st = np.zeros(8)
    daystart = 0.0; cur = -1
    px = np.zeros(max(nsub + 1, 4)); z = np.zeros(nsub + 1)
    for i in range(n):
        if day[i] != cur:
            cur = day[i]; daystart = st[6]
        a = spr[i]
        worst = 1e18; lmax = int(st[0])
        if path == 3:
            nv = _bridge(o[i], h[i], l[i], c[i], nsub, px, z)
        else:
            if h[i] > l[i]:
                if path == 0:
                    up_first = np.random.random() < 0.5 * ((o[i] - l[i]) + (h[i] - c[i])) / (h[i] - l[i])
                elif path == 1:
                    up_first = not (c[i] > o[i])
                else:
                    up_first = st[1] == 1
            else:
                up_first = True
            px[0] = o[i]
            if up_first:
                px[1] = h[i]; px[2] = l[i]
            else:
                px[1] = l[i]; px[2] = h[i]
            px[3] = c[i]; nv = 4
        p = c[i - 1] if i > 0 else o[i]
        for v in range(nv):
            q = px[v]
            if st[0] > 0:
                nb = _seg(st, p, q, v == 0, a, step, maxlev, btp, bsl, i, day, dpnl, dpos, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
            p = q
            if st[0] > lmax: lmax = int(st[0])
            fl = _float(st, q, a)
            if st[0] > 0 and fl < st[5]: st[5] = fl
            if st[6] + fl < worst: worst = st[6] + fl
            if st[6] + fl - daystart < dmin[day[i]]: dmin[day[i]] = st[6] + fl - daystart
        if st[0] > 0 and ((tmax > 0 and i - int(st[4]) >= tmax) or tod[i] >= END_TOD or last[i] or i == n - 1):
            nb = _close_b(st, _float(st, c[i], a), i, 2, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
        if st[0] == 0 and dirsig[i] != 0 and tod[i] <= LAST_ENTRY_TOD and tod[i] >= FIRST_ENTRY_TOD and not last[i] and i < n - 1:
            d = dirsig[i]
            e = c[i] + a if d == 1 else c[i]
            st[0] = 1; st[1] = d; st[2] = e; st[3] = e; st[4] = i; st[5] = 0.0
            dpos[day[i]] += 1; dbask[day[i]] += 1
            fl = _float(st, c[i], a)
            if st[6] + fl < worst: worst = st[6] + fl
            if lmax < 1: lmax = 1
        eq_min[i] = worst if worst < 1e17 else st[6]
        lev_max[i] = lmax
    return dpnl, dbask, dpos, dmin, eq_min, lev_max, b_pnl[:nb], b_lev[:nb], b_dur[:nb], b_why[:nb], b_start[:nb], b_mae[:nb]


def run_grid(H, dirsig, step, maxlev, btp, bsl=0.0, tmax=0, path='FAIR', spread='base', seed=0, nsub=30):
    sig = np.sign(np.nan_to_num(np.asarray(dirsig, float))).astype(np.int64)
    r = _grid(H.o, H.h, H.l, H.c, H._spr[spread], H.tod, H.day, H.last, sig, float(step), int(maxlev), float(btp),
              float(bsl), int(tmax), PATH[path], int(seed), int(nsub))
    dp, db, dpos, dmin, eqm, levm, bp, bl, bd, bw, bs, bm = r
    days = pd.DataFrame({'pnl': dp, 'baskets': db, 'positions': dpos, 'intraday_min': dmin}, index=H.dates)
    bask = pd.DataFrame({'start': H.m1.index[bs], 'pnl': bp, 'levels': bl, 'bars': bd, 'why': bw, 'mae': bm})
    return days, bask, eqm, levm


def gsumm(H, days, bask, eqm, levm, period=None, account=3000.0, leverage=(100, 500), stop_out=0.5):
    """Daily stats + drawdowns including floating losses + margin stop-out check for a `account` $ account
    (0.01 lot = 1 oz; margin per position = price / leverage; stop-out when equity < stop_out x margin)."""
    mi = H.m1.index
    selm = np.ones(len(mi), bool); seld = np.ones(len(days), bool); selb = np.ones(len(bask), bool)
    if period == 'train': selm = mi < SPLIT; seld = days.index < SPLIT; selb = (bask.start < SPLIT).values
    if period == 'test': selm = mi >= SPLIT; seld = days.index >= SPLIT; selb = (bask.start >= SPLIT).values
    d = days[seld]; p = d.pnl; b = bask[selb]
    eqr = p.cumsum()
    eq = eqm[selm]
    if period == 'test': eq = eq - days.pnl[~seld].sum()     # equity relative to the start of TEST
    peak = np.maximum.accumulate(np.r_[0.0, eq])[1:]
    out = dict(per_day=p.mean(), baskets_day=d.baskets.mean(), positions_day=d.positions.mean(),
               per_basket=b.pnl.mean() if len(b) else np.nan, basket_win=(b.pnl > 0).mean() if len(b) else np.nan,
               per_position=p.sum() / max(d.positions.sum(), 1),
               days_ge5=(p >= 4.99).mean(), losing_days=(p < 0).mean(), worst_day=p.min(), best_day=p.max(),
               worst_intraday=d.intraday_min.min(), max_dd_closed=(eqr - eqr.cummax()).min(),
               max_dd_float=(eq - peak).min() if len(eq) else np.nan, min_equity=eq.min() if len(eq) else np.nan,
               worst_basket=b.pnl.min() if len(b) else np.nan, worst_mae=b.mae.min() if len(b) else np.nan,
               max_levels=int(levm[selm].max()) if selm.any() else 0, stops=(b.why == 1).mean() if len(b) else np.nan,
               total=p.sum(), days=len(p))
    price = H.c[selm]; lv = levm[selm]
    for L in leverage:
        margin = lv * price / L
        lvl = np.where(margin > 0, (account + eq) / np.maximum(margin, 1e-9), np.inf)
        bad = (account + eq <= 0) | (lvl < stop_out)
        out[f'stopout_1to{L}'] = bool(bad.any())
        out[f'min_margin_level_1to{L}'] = float(lvl.min()) if len(lvl) else np.nan
    return out
