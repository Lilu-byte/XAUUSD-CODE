"""Entry-grid scalper on OHLC bars (David, 2026-10-20).
Levels every G dollars (multiples of G). When the bid touches a level, open one
0.01 lot in the direction of the forming candle (bid at touch vs bar open):
buy at ask (= bid + spread), sell at bid. TP = TP dollars of profit, optional SL.
One open trade per level at a time. Intra-bar path: O-L-H-C for up bars,
O-H-L-C for down bars, straight lines between. 0.01 lot: $1 per $1 move.
Cost: bar spread (points*0.01) + slip. Swap per open trade per night."""
import heapq, random
import numpy as np, pandas as pd

SWAP_L, SWAP_S = 0.126, 0.046

def load(path):
    d = pd.read_csv(path)
    d['t'] = pd.to_datetime(d['time'], format='%Y.%m.%d %H:%M')
    return d

def run(d, G, TP, SL=None, slip=0.05, dirmode='candle', seed=0, maxopen=None, path_mode='near'):
    rng = random.Random(seed)
    # integer cents throughout (no float drift at level boundaries)
    o, h, l, c = (np.rint(d[k].to_numpy() * 100).astype(np.int64).tolist() for k in ('open', 'high', 'low', 'close'))
    sp = (d['spread'].to_numpy() + round(slip * 100)).astype(np.int64).tolist()
    G = round(G * 100); TP = round(TP * 100); SL = round(SL * 100) if SL else None
    day = d['t'].dt.date.to_numpy(); wd = d['t'].dt.weekday.to_numpy()
    longs_tp, longs_sl, shorts_tp, shorts_sl = [], [], [], []   # heaps
    pos = {}            # id -> (side, entry, level, alive)
    busy = set()        # levels with an open trade
    nid = 0; realized = 0.0; trades = wins = 0
    nL = nS = 0; sumL = sumS = 0.0
    eq_peak = 0.0; maxdd = 0.0; daily = {}; maxopen_seen = 0; nights = 0

    def close(i, px_bid, s):
        nonlocal realized, trades, wins, nL, nS, sumL, sumS
        side, e, lev, alive = pos[i]
        if not alive: return
        pos[i] = (side, e, lev, False); busy.discard(lev)
        pnl = (px_bid - e) if side > 0 else (e - (px_bid + s))
        pnl /= 100.0
        realized += pnl; trades += 1; wins += pnl > 0
        daily[cur_day] = daily.get(cur_day, 0.0) + pnl
        if side > 0: nL -= 1; sumL -= e
        else: nS -= 1; sumS -= e

    prev_day = None
    for b in range(len(o)):
        cur_day = day[b]; s = sp[b]
        if prev_day is not None and cur_day != prev_day:   # overnight swap
            mult = 3 if wd[b] == 3 else 1                  # Wed->Thu triple
            sw = -(nL * SWAP_L + nS * SWAP_S) * mult
            realized += sw; daily[cur_day] = daily.get(cur_day, 0.0) + sw
            nights += nL + nS
        prev_day = cur_day
        upbar = c[b] >= o[b]
        if path_mode == 'far': upbar = not upbar   # opposite wick first
        path = [o[b], l[b], h[b], c[b]] if upbar else [o[b], h[b], l[b], c[b]]
        for a, z in zip(path[:-1], path[1:]):
            if a == z: continue
            up = z > a
            cur = a
            while True:
                # candidate events strictly beyond cur, up to z
                if up:
                    nxt_lev = (cur // G + 1) * G
                    cands = [(nxt_lev, 'lev')]
                    while longs_tp and not pos[longs_tp[0][1]][3]: heapq.heappop(longs_tp)
                    while shorts_sl and not pos[shorts_sl[0][1]][3]: heapq.heappop(shorts_sl)
                    if longs_tp: cands.append((longs_tp[0][0], 'ltp'))
                    if shorts_sl: cands.append((shorts_sl[0][0], 'ssl'))
                    px, kind = min(cands)
                    if px > z: break
                    px = max(px, cur)      # stop already beyond price: fills now
                else:
                    nxt_lev = -((-cur) // G) * G - G
                    cands = [(-nxt_lev, 'lev')]
                    while shorts_tp and not pos[shorts_tp[0][1]][3]: heapq.heappop(shorts_tp)
                    while longs_sl and not pos[longs_sl[0][1]][3]: heapq.heappop(longs_sl)
                    if shorts_tp: cands.append((shorts_tp[0][0], 'stp'))
                    if longs_sl: cands.append((longs_sl[0][0], 'lsl'))
                    npx, kind = min(cands); px = -npx
                    if px < z: break
                    px = min(px, cur)
                cur = px
                if kind == 'lev':
                    lev = px
                    if lev in busy: continue
                    if maxopen and nL + nS >= maxopen: continue
                    if dirmode == 'candle':
                        side = 1 if px > o[b] else (-1 if px < o[b] else 0)
                    elif dirmode == 'against':
                        side = -1 if px > o[b] else (1 if px < o[b] else 0)
                    else:
                        side = rng.choice((1, -1))
                    if side == 0: continue
                    nid += 1; busy.add(lev)
                    if side > 0:
                        e = px + s; pos[nid] = (1, e, lev, True); nL += 1; sumL += e
                        heapq.heappush(longs_tp, (e + TP, nid))
                        if SL: heapq.heappush(longs_sl, (-(e - SL), nid))
                    else:
                        e = px; pos[nid] = (-1, e, lev, True); nS += 1; sumS += e
                        heapq.heappush(shorts_tp, (-(e - TP - s), nid))
                        if SL: heapq.heappush(shorts_sl, (e + SL - s, nid))
                    maxopen_seen = max(maxopen_seen, nL + nS)
                else:
                    heap = {'ltp': longs_tp, 'ssl': shorts_sl, 'stp': shorts_tp, 'lsl': longs_sl}[kind]
                    _, i = heapq.heappop(heap); close(i, px, s)
        # mark to market at bar close
        fl = ((nL * c[b] - sumL) + (sumS - nS * (c[b] + s))) / 100.0
        eq = realized + fl
        eq_peak = max(eq_peak, eq); maxdd = min(maxdd, eq - eq_peak)
    ndays = len(set(day))
    dv = np.array(list(daily.values())) if daily else np.zeros(1)
    return dict(G=G / 100, TP=TP / 100, SL=(SL or 0) / 100, dir=dirmode, trades=trades,
                trades_day=trades / ndays, win=wins / max(trades, 1),
                realized=realized, floating=fl, net=realized + fl,
                net_day=(realized + fl) / ndays, per_trade=realized / max(trades, 1),
                maxdd=maxdd, open_end=nL + nS, max_open=maxopen_seen,
                days=ndays)
