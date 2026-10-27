"""Rebuilds that need their own loop (pending orders that live for days, baskets, open-price-only logic).
Same costs as gbt.py: spread $0.30, slippage $0.10 on market/stop fills, stop first when both levels are in one bar.
Each returns (data, trades) with the columns gbt.stats() expects."""
import numpy as np, pandas as pd
from gbt import load, htf, ema, atr, simulate, SPREAD, SLIP

SP = SPREAD


def _df(rows):
    t = pd.DataFrame(rows, columns=['entry_time', 'exit_time', 'dir', 'entry', 'exit', 'pnl', 'why'])
    t['gross'] = t.pnl; t['swap'] = 0.0
    return t


# ---------- ikeawesom PDH/PDL sweep, "70% win rate" (bar opens only, faithful inverted bias) ----------
def ikeawesom(tf='M15', fix_bias=False):
    d = load(tf); days = d.index.normalize(); rows = []; wins_def = []
    g = list(d.groupby(days))
    for k in range(1, len(g)):
        prev = g[k - 1][1]; cur = g[k][1]
        PDH, PDL = prev.high.max(), prev.low.min()
        long_mode = (prev.open - prev.close).sum() >= 0
        if fix_bias: long_mode = not long_mode
        O = cur.open.values; T = cur.index
        state = 0; swept = False; sweep = 0.0; ent = 0.0; et = None
        for j in range(len(O)):
            p = O[j]
            if state == 1:
                if (long_mode and p > sweep) or (not long_mode and p < sweep):
                    x = p - SLIP if long_mode else p + SP + SLIP
                    rows.append((et, T[j], 1 if long_mode else -1, ent, x, (x - ent) if long_mode else (ent - x), 'author_WIN'))
                    state = 0; swept = False; continue
                elif p == sweep: continue
                else:
                    x = p - SLIP if long_mode else p + SP + SLIP
                    rows.append((et, T[j], 1 if long_mode else -1, ent, x, (x - ent) if long_mode else (ent - x), 'author_LOSE'))
                    state = 0; break
            elif not swept:
                if (long_mode and p <= PDL) or (not long_mode and p >= PDH): swept = True; sweep = p
            else:
                if (long_mode and p >= sweep) or (not long_mode and p <= sweep):
                    state = 1; et = T[j]; ent = p + SP + SLIP if long_mode else p - SLIP
                else: sweep = p
        if state == 1:
            p = cur.close.values[-1]; x = p - SLIP if long_mode else p + SP + SLIP
            rows.append((et, T[-1], 1 if long_mode else -1, ent, x, (x - ent) if long_mode else (ent - x), 'author_BE'))
    return d, _df(rows)


# ---------- AhadRasheed PDH/PDL break-and-reverse, stop entry, 2R ----------
def ahad(tf='M5', reset_daily=False):
    d = load(tf); O, H, L, C = (d[x].values for x in ('open', 'high', 'low', 'close'))
    days = d.index.normalize(); dh = d.high.groupby(days).max(); dl = d.low.groupby(days).min()
    pdh = pd.Series(days).map(dh.shift()).values; pdl = pd.Series(days).map(dl.shift()).values
    n = len(d); sig = np.zeros(n); lvl = np.zeros(n); sld = np.zeros(n)
    st = 'idle'; ext = 0.0; rh = rl = 0.0
    for i in range(n):
        if np.isnan(pdh[i]): continue
        if reset_daily and i > 0 and days[i] != days[i - 1]: st = 'idle'
        if st == 'idle':
            if L[i] < pdl[i]: st, ext = 'lw', L[i]
            elif H[i] > pdh[i]: st, ext = 'sg', H[i]
        elif st == 'lw':
            if C[i] > O[i] and C[i] < pdl[i]: st, rh = 'lb', H[i]
            else: ext = min(ext, L[i])
        elif st == 'lb':
            if C[i] >= pdl[i] and H[i] < rh: st = 'idle'
            elif H[i] > rh: st = 'idle'
        elif st == 'sg':
            if C[i] > O[i] and C[i] > pdh[i]: st = 'sr'
            else: ext = max(ext, H[i])
        elif st == 'sr':
            if C[i] < O[i] and C[i] > pdh[i]: st, rl = 'sb', L[i]
            else: ext = max(ext, H[i])
        elif st == 'sb':
            if L[i] < rl: st = 'idle'
        # a pending stop order for the next bar
        if st == 'lb' and ext < rh: sig[i], lvl[i], sld[i] = 1, rh, rh - ext
        if st == 'sb' and ext > rl: sig[i], lvl[i], sld[i] = -1, rl, ext - rl
    t = simulate(d, sig, sl=sld, tp=2 * sld, ent_px=lvl)
    return d, t


# ---------- coler07 martingale grid (M15, intended EMA logic) ----------
def martingale(tf='M15', step=5.0, mult=2.0, max_orders=8, target=1.0, account=3000.0):
    d = load(tf); O, L, H = d.open.values, d.low.values, d.high.values
    f, s = ema(d.close, 10).values, ema(d.close, 30).values; T = d.index
    rows = []; pos = []; dirn = 0; worst_float = 0.0; t0 = None; realized = 0.0; blown = None
    for i in range(1, len(d)):
        bid = O[i]; ask = bid + SP
        if pos:
            px = ask if dirn == 1 else bid
            if len(pos) < max_orders and abs(px - pos[-1][0]) >= step:
                pos.append((px + SLIP * dirn, mult ** len(pos)))
            fl = sum(q * ((bid - e) if dirn == 1 else (e - ask)) for e, q in pos)
            if fl >= target:
                rows.append((t0, T[i], dirn, pos[0][0], bid, fl - SLIP * sum(q for _, q in pos), f'basket_{len(pos)}'))
                realized += rows[-1][5]
                pos = []
            else:
                adverse = L[i] if dirn == 1 else H[i] + SP
                wf = sum(q * ((adverse - e) if dirn == 1 else (e - adverse)) for e, q in pos)
                worst_float = min(worst_float, wf)
                if blown is None and account + realized + wf <= 0: blown = (T[i], realized, wf)
        if not pos:
            dirn = 1 if f[i - 1] > s[i - 1] else -1
            pos = [((ask + SLIP) if dirn == 1 else (bid - SLIP), 1.0)]; t0 = T[i]
    return d, _df(rows), worst_float, blown


# ---------- foeed FvgGold (M15 fair value gaps, limit orders that never expire) ----------
def fvggold(tf='M15', cancel_stale=False):
    d = load(tf); O, H, L, C = (d[x].values for x in ('open', 'high', 'low', 'close'))
    a = atr(d, 14).values; T = d.index; hr = T.hour.values; n = len(d)
    h1 = load('H1'); e50 = htf(d, 'H1', ema(h1.close, 50).values); e200 = htf(d, 'H1', ema(h1.close, 200).values)
    days = T.normalize()
    zones = []  # dict(type, top, bot, mid, born, ordered)
    pend = None; pos = None; rows = []; dpnl = {}
    for t in range(4, n):
        day = days[t]; bias = 1 if e50[t] > e200[t] else (-1 if e50[t] < e200[t] else 0)
        # 1) new zone from the three bars just closed (c1=t-3, middle=t-2, c3=t-1)
        c1, m, c3 = t - 3, t - 2, t - 1
        for typ, top, bot in ((1, L[c3], H[c1]), (-1, L[c1], H[c3])):
            gap = top - bot
            if gap >= 0.25 and not np.isnan(a[t - 1]):
                rg = H[m] - L[m]
                sc = min(gap / a[t - 1], 1) * 30 + (abs(C[m] - O[m]) / rg * 30 if rg > 0 else 0) + (20 if typ == bias else 0) \
                     + (1 - 2 / 20) * 10 + (10 if (typ == 1 and C[t - 1] < e50[t]) or (typ == -1 and C[t - 1] > e50[t]) else 0)
                if sc >= 50: zones.append(dict(type=typ, top=top, bot=bot, mid=(top + bot) / 2, born=m, ordered=False))
        # 2) open position on bar t
        if pos is not None:
            dirn, ent, sl, tp, et = pos; x = None
            if dirn == 1:
                if L[t] <= sl: x, why = min(O[t], sl) - SLIP, 'stop'
                elif H[t] >= tp: x, why = tp, 'target'
            else:
                if H[t] + SP >= sl: x, why = max(O[t] + SP, sl) + SLIP, 'stop'
                elif L[t] + SP <= tp: x, why = tp, 'target'
            if x is not None:
                p = (x - ent) * dirn; rows.append((et, T[t], dirn, ent, x, p, why)); dpnl[day] = dpnl.get(day, 0) + p; pos = None
            else:
                fav = (H[t] - ent) if dirn == 1 else (ent - L[t] - SP)
                if fav >= 0.5 * a[t - 1] and ((dirn == 1 and sl < ent) or (dirn == -1 and sl > ent)):
                    pos = (dirn, ent, ent + 0.02 * dirn, tp, et)
            continue
        # 3) pending limit order fills?
        if pend is not None and cancel_stale and (t - pend[4] > 20 or
                (pend[0] == 1 and L[t - 1] < pend[5]) or (pend[0] == -1 and H[t - 1] + SP > pend[5])):
            pend = None
        if pend is not None:
            dirn, lv, slv, tpv = pend[:4]
            hit = (L[t] + SP <= lv) if dirn == 1 else (H[t] >= lv)
            if hit:
                ent = min(lv, O[t] + SP) if dirn == 1 else max(lv, O[t])
                pend = None
                # same bar: stop only (conservative)
                if (dirn == 1 and L[t] <= slv) or (dirn == -1 and H[t] + SP >= slv):
                    x = slv - SLIP if dirn == 1 else slv + SLIP; p = (x - ent) * dirn
                    rows.append((T[t], T[t], dirn, ent, x, p, 'stop')); dpnl[day] = dpnl.get(day, 0) + p
                else:
                    pos = (dirn, ent, slv, tpv, T[t])
            continue
        # 4) zone housekeeping: invalidate by midpoint, expire after 20 bars
        zones = [z for z in zones if t - z['born'] <= 20 and not (z['type'] == 1 and L[t - 1] < z['mid'])
                 and not (z['type'] == -1 and H[t - 1] + SP > z['mid'])]
        # 5) place a new limit order
        if not ((7 <= hr[t] < 10) or (12 <= hr[t] < 21)) or dpnl.get(day, 0) <= -5: continue
        for z in zones:
            if z['type'] != bias or z['ordered']: continue
            if z['type'] == 1:
                lv = z['bot'] + 1.5
                if O[t] + SP - lv < SP: continue
                pend = (1, lv, z['bot'] - 3.0, lv + 6.75, z['born'], z['mid'])
            else:
                lv = z['top'] - 1.5
                if lv - O[t] < SP: continue
                pend = (-1, lv, z['top'] + 3.0 + SP, lv - 6.75, z['born'], z['mid'])
            z['ordered'] = True; break
    return d, _df(rows)
