"""Averaging-down / grid basket simulator (own code; mlib conventions: bid candles, long fills at ask = bid + spread,
short exits at ask, signals/new baskets at bar close, flat at the close of each day's last bar (22:59 server) unless carry=True; no new basket after 22:45).

Basket rules:  when flat, at the close of bar i with dirsig[i] != 0, open 1 position (0.01 lot) in that direction.
While the basket is open, every time price moves `step` $ against the LAST entry, add one more position (up to `maxlev`).
Close ALL positions when the basket's combined floating profit reaches `btp` $ (0.10-1.00 range), or when it
reaches -`bsl` $ (0 = no basket stop), or after `tmax` bars (0 = no limit), or at 23:30 (unless carry).
A new basket can only start at a bar close (never inside the bar it closed in).

Inside each M1 bar the path is O -> first extreme -> second extreme -> C (straight segments). Which extreme comes
first: 'FAIR' = random with P(high first) = average of (o-l)/(h-l) and (h-c)/(h-l) (gambler's-ruin odds from the
open and, time-reversed, from the close); 'OHLC' = MT5 1-minute-OHLC path (bull bar O-L-H-C, bear/flat O-H-L-C);
'ADV' = worst order for the basket (long: high first then low; short: low first then high).
Levels crossed by a jump at the bar open fill at the open. Levels crossed inside a segment fill exactly at the level.
Equity (realised + floating, marked at bid for longs / ask for shorts) is tracked at every path vertex.
"""
import numpy as np, pandas as pd
from numba import njit

PATH = {'FAIR': 0, 'OHLC': 1, 'ADV': 2}
END_TOD = 23 * 60 + 30
LAST_NEW = 22 * 60 + 45     # no new basket from 22:45 server (last bar of the day is 22:59)


@njit(cache=True)
def _close(val, nlev, i, t0, why, mae, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb):
    dpnl[day[t0]] += val
    b_pnl[nb] = val; b_lev[nb] = nlev; b_dur[nb] = i - t0; b_why[nb] = why; b_start[nb] = t0; b_mae[nb] = mae
    return nb + 1


@njit(cache=True)
def _grid(o, h, l, c, spr, tod, day, dirsig, step, maxlev, btp, bsl, tmax, carry, path, seed):
    """why: 0 = basket target, 1 = basket stop, 2 = timeout / 23:30 / end of data, 3 = day change (flat mode)."""
    np.random.seed(seed)
    n = len(c); nd = day[-1] + 1
    dpnl = np.zeros(nd); dbask = np.zeros(nd); dpos = np.zeros(nd); dmin = np.zeros(nd)
    eq_min = np.zeros(n)
    b_pnl = np.zeros(n); b_lev = np.zeros(n, np.int64); b_dur = np.zeros(n, np.int64); b_why = np.zeros(n, np.int64)
    b_start = np.zeros(n, np.int64); b_mae = np.zeros(n)
    nb = 0
    nlev = 0; d = 0; E = 0.0; last = 0.0; t0 = 0; mae = 0.0
    cum = 0.0; daystart = 0.0; cur = -1; maxpos = 0
    px = np.zeros(4)
    for i in range(n):
        if day[i] != cur:
            cur = day[i]; daystart = cum
        a = spr[i]
        worst = 1e18
        if nlev > 0 and (not carry) and day[i] != day[t0]:
            val = (nlev * o[i] - E) if d == 1 else (E - nlev * (o[i] + a))
            cum += val; nb = _close(val, nlev, i, t0, 3, mae, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
            nlev = 0; E = 0.0
        up_first = False
        if h[i] > l[i]:
            if path == 0:
                pu = 0.5 * ((o[i] - l[i]) + (h[i] - c[i])) / (h[i] - l[i])
                up_first = np.random.random() < pu
            elif path == 1:
                up_first = not (c[i] > o[i])
            else:
                up_first = (d == 1)
        px[0] = o[i]
        if up_first:
            px[1] = h[i]; px[2] = l[i]
        else:
            px[1] = l[i]; px[2] = h[i]
        px[3] = c[i]
        p = o[i]                      # current price along the path
        for v in range(4):
            q = px[v]
            # move from p to q, processing events in order; v == 0 is the jump to the open (fills at the open)
            for _ in range(maxlev + 3):
                if nlev == 0: break
                if d == 1:
                    lt = (E + btp) / nlev
                    la = last - step - a if nlev < maxlev else -1e18
                    ls = (E - bsl) / nlev if bsl > 0 else -1e18
                    if q >= p:                                   # rising (or the open jump): target first
                        if lt <= q + 1e-12:
                            fill = max(lt, p)
                            val = nlev * fill - E; cum += val
                            nb = _close(val, nlev, i, t0, 0, mae, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
                            nlev = 0; E = 0.0; p = fill
                        if v > 0 or nlev == 0: break
                    lv = max(la, ls)                             # falling: highest adverse level first
                    if lv < -1e17 or lv < q - 1e-12: break
                    fill = min(lv, p)
                    if ls >= la:
                        val = nlev * fill - E; cum += val
                        nb = _close(val, nlev, i, t0, 1, mae, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
                        nlev = 0; E = 0.0; p = fill; break
                    e = fill + a; nlev += 1; E += e; last = e; dpos[day[i]] += 1; p = fill
                    if nlev > maxpos: maxpos = nlev
                else:
                    lt = (E - btp) / nlev - a
                    la = last + step if nlev < maxlev else 1e18
                    ls = (E + bsl) / nlev - a if bsl > 0 else 1e18
                    if q <= p:                                   # falling (or open jump): target first
                        if lt >= q - 1e-12:
                            fill = min(lt, p)
                            val = E - nlev * (fill + a); cum += val
                            nb = _close(val, nlev, i, t0, 0, mae, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
                            nlev = 0; E = 0.0; p = fill
                        if v > 0 or nlev == 0: break
                    lv = min(la, ls)                             # rising: lowest adverse level first
                    if lv > 1e17 or lv > q + 1e-12: break
                    fill = max(lv, p)
                    if ls <= la:
                        val = E - nlev * (fill + a); cum += val
                        nb = _close(val, nlev, i, t0, 1, mae, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
                        nlev = 0; E = 0.0; p = fill; break
                    e = fill; nlev += 1; E += e; last = e; dpos[day[i]] += 1; p = fill
                    if nlev > maxpos: maxpos = nlev
            p = q
            fl = 0.0
            if nlev > 0:
                fl = (nlev * q - E) if d == 1 else (E - nlev * (q + a))
                if fl < mae: mae = fl
            if cum + fl < worst: worst = cum + fl
            if cum + fl - daystart < dmin[day[i]]: dmin[day[i]] = cum + fl - daystart
        lastbar = (i == n - 1) or (day[i + 1] != day[i])
        if nlev > 0 and ((tmax > 0 and i - t0 >= tmax) or ((not carry) and (tod[i] >= END_TOD or lastbar)) or i == n - 1):
            val = (nlev * c[i] - E) if d == 1 else (E - nlev * (c[i] + a)); cum += val
            nb = _close(val, nlev, i, t0, 2, mae, day, dpnl, b_pnl, b_lev, b_dur, b_why, b_start, b_mae, nb)
            nlev = 0; E = 0.0
        if nlev == 0 and dirsig[i] != 0 and tod[i] < LAST_NEW and not lastbar and i < n - 1:
            d = dirsig[i]
            e = c[i] + a if d == 1 else c[i]
            nlev = 1; E = e; last = e; t0 = i; mae = 0.0; dpos[day[i]] += 1; dbask[day[i]] += 1
            if maxpos < 1: maxpos = 1
        eq_min[i] = worst if worst < 1e17 else cum
    return dpnl, dbask, dpos, dmin, eq_min, b_pnl[:nb], b_lev[:nb], b_dur[:nb], b_why[:nb], b_start[:nb], b_mae[:nb], maxpos


def run_grid(H, dirsig, step, maxlev, btp, bsl=0.0, tmax=0, carry=False, path='FAIR', spread='base', seed=0):
    sig = np.nan_to_num(np.asarray(dirsig, float)).astype(np.int64)
    r = _grid(H.o, H.h, H.l, H.c, H._spr[spread], H.tod, H.day, sig, float(step), int(maxlev), float(btp), float(bsl),
              int(tmax), bool(carry), PATH[path], int(seed))
    dp, db, dpos, dmin, eqm, bp, bl, bd, bw, bs, bm, maxpos = r
    days = pd.DataFrame({'pnl': dp, 'baskets': db, 'positions': dpos, 'intraday_min': dmin}, index=H.dates)
    bask = pd.DataFrame({'start': H.m1.index[bs], 'pnl': bp, 'levels': bl, 'bars': bd, 'why': bw, 'mae': bm})
    return days, bask, eqm, maxpos


def gsumm(days, bask, eqm, maxpos, H, period=None):
    from mlib import SPLIT
    sel = np.ones(len(days), bool)
    if period == 'train': sel = days.index < SPLIT
    if period == 'test': sel = days.index >= SPLIT
    d = days[sel]; p = d.pnl
    bsel = (bask.start < SPLIT) if period == 'train' else ((bask.start >= SPLIT) if period == 'test' else np.ones(len(bask), bool))
    b = bask[bsel]
    # equity drawdown including floating losses (eq_min per bar vs running peak of realised equity)
    mi = H.m1.index
    bsel_m = (mi < SPLIT) if period == 'train' else ((mi >= SPLIT) if period == 'test' else np.ones(len(mi), bool))
    eq = eqm[bsel_m]
    base = days.pnl[~sel].sum() if period == 'test' else 0.0  # not needed: drawdown is relative
    peak = np.maximum.accumulate(np.r_[eq[0], eq])[1:]
    float_dd = (eq - np.maximum.accumulate(eq)).min() if len(eq) else np.nan
    eqr = p.cumsum()
    return dict(per_day=p.mean(), baskets_day=d.baskets.mean(), positions_day=d.positions.mean(),
                per_basket=b.pnl.mean() if len(b) else np.nan, basket_win=(b.pnl > 0).mean() if len(b) else np.nan,
                days_ge5=(p >= 4.99).mean(), losing_days=(p < 0).mean(), worst_day=p.min(), best_day=p.max(),
                worst_intraday=d.intraday_min.min(), max_dd_closed=(eqr - eqr.cummax()).min(), max_dd_float=float_dd,
                worst_basket=b.pnl.min() if len(b) else np.nan, worst_basket_mae=b.mae.min() if len(b) else np.nan,
                max_levels=b.levels.max() if len(b) else 0, stops=(b.why == 1).mean() if len(b) else np.nan,
                total=p.sum(), days=len(p))
