"""Line-by-line Python port of the v1.30 MQL5 signal code (GoldMicroScalp.mq5 / GoldMicroScalpSignals.mq5).
Extends ../signal-parity/port.py (v1.10). Arrays are SERIES-ordered (index 0 = newest bar), exactly like
MqlRates r[] after ArraySetAsSeries(r, true). Indices are absolute positions in the reversed full array and
'total' is the absolute upper bound, so every `j < total` / `i + 240 >= total` test is the MQL5 one.
The M5 series (for M5Dir) is kept CHRONOLOGICAL (T5[0] oldest), with iBarShift / iTime / iOpen / iClose /
CopyBuffer emulated on it; E5 is MT5's iMA(MODE_EMA) recursion over the whole M5 export.
"""
import numpy as np
from numba import njit

M5_OFF, M5_CANDLE, M5_EMA = 0, 1, 2


# --- GoldMicroScalp.mq5:192-229 -------------------------------------------------------------------------
@njit(cache=True)
def SigPullback(T, O, H, L, C, i, total, n, k, maru, minBody, trend):
    if trend == 0 or n < 1:
        return 0
    sec = n * 60
    t = T[i]
    if (t + 60) % sec != 0:
        return 0
    co = np.empty(21); cc = np.empty(21); ch = np.empty(21); cl = np.empty(21)
    nc = 0; key = -1
    for j in range(i, total):
        kj = T[j] - (T[j] % sec)
        if kj != key:
            if nc == 21:
                break
            key = kj
            cc[nc] = C[j]; ch[nc] = H[j]; cl[nc] = L[j]; co[nc] = O[j]
            nc += 1
        else:
            ch[nc - 1] = max(ch[nc - 1], H[j])
            cl[nc - 1] = min(cl[nc - 1], L[j])
            co[nc - 1] = O[j]
    if nc < 21:
        return 0
    body0 = abs(cc[0] - co[0]); rng0 = ch[0] - cl[0]
    if rng0 <= 0:
        return 0
    avg = 0.0; avgR = 0.0
    for c in range(1, 21):
        avg += abs(cc[c] - co[c]); avgR += ch[c] - cl[c]
    avg /= 20.0; avgR /= 20.0
    if body0 >= k * avg and body0 >= maru * rng0 and body0 >= minBody * avgR:
        d = -1 if cc[0] > co[0] else (1 if cc[0] < co[0] else 0)
        return d if d == trend else 0
    return 0


# --- :233-243 --------------------------------------------------------------------------------------------
@njit(cache=True)
def SigSpikeFade(T, O, H, L, C, i, total, mult, vwap):
    if i + 240 >= total or vwap <= 0:
        return 0
    atr = 0.0
    for j in range(i, i + 240):
        atr += H[j] - L[j]
    atr /= 240.0
    r1 = C[i] - C[i + 1]
    if r1 > mult * atr and C[i] > vwap:
        return -1
    if r1 < -mult * atr and C[i] < vwap:
        return 1
    return 0


# --- :247-277 --------------------------------------------------------------------------------------------
@njit(cache=True)
def SigQuarterFade(T, O, H, L, C, i, total, k, h0, h1):
    t = T[i]
    if t % 900 != 0:
        return 0
    hour = (t % 86400) // 3600
    if hour < h0 or hour > h1:
        return 0
    qh = np.empty(12); ql = np.empty(12); qk = np.empty(12, np.int64)
    nq = 0; key = -1
    for j in range(i + 1, total):
        kj = T[j] - (T[j] % 900)
        if kj != key:
            if nq == 12:
                break
            key = kj; qk[nq] = kj; qh[nq] = H[j]; ql[nq] = L[j]; nq += 1
        else:
            qh[nq - 1] = max(qh[nq - 1], H[j])
            ql[nq - 1] = min(ql[nq - 1], L[j])
    if nq < 12 or qk[0] != t - 900:
        return 0
    ar = 0.0
    for q in range(12):
        ar += qh[q] - ql[q]
    ar /= 12.0
    if C[i] > qh[0] + k * ar:
        return -1
    if C[i] < ql[0] - k * ar:
        return 1
    return 0


# --- :280-292 --------------------------------------------------------------------------------------------
@njit(cache=True)
def SessionVWAP(T, H, L, C, V, i, total):
    t = T[i]
    dayStart = t - (t % 86400)
    pv = 0.0; v = 0.0
    j = i
    while j < total and T[j] >= dayStart:
        tv = float(V[j])
        pv += (H[j] + L[j] + C[j]) / 3.0 * tv
        v += tv
        j += 1
    return pv / v if v > 0 else 0.0


@njit(cache=True)
def _body(O, C, k): return abs(C[k] - O[k])
@njit(cache=True)
def _up(O, H, C, k): return H[k] - max(O[k], C[k])
@njit(cache=True)
def _lo(O, L, C, k): return min(O[k], C[k]) - L[k]


PATDIR = np.array([1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1], np.int64)


# --- :314-353 --------------------------------------------------------------------------------------------
@njit(cache=True)
def DetectPatterns(O, H, L, C, i, hit):
    for p in range(16):
        hit[p] = False
    avg = 0.0
    for k in range(1, 21):
        avg += _body(O, C, i + k)
    avg /= 20.0
    body = _body(O, C, i); rng = H[i] - L[i]; up = _up(O, H, C, i); lo = _lo(O, L, C, i)
    if rng <= 0:
        return
    c = C[i]; o = O[i]; c1 = C[i + 1]; o1 = O[i + 1]; b1 = _body(O, C, i + 1)
    c2 = C[i + 2]; o2 = O[i + 2]; b2 = _body(O, C, i + 2)
    down = C[i + 1] < C[i + 6]; upt = C[i + 1] > C[i + 6]
    long1 = b1 > avg; long2 = b2 > avg
    bull0 = C[i] > O[i]; bear0 = C[i] < O[i]
    bull1 = C[i + 1] > O[i + 1]; bear1 = C[i + 1] < O[i + 1]
    bull2 = C[i + 2] > O[i + 2]; bear2 = C[i + 2] < O[i + 2]
    hammerShape = lo >= 2 * body and up <= 0.5 * body + 0.05 * rng and body <= 0.35 * rng
    invShape = up >= 2 * body and lo <= 0.5 * body + 0.05 * rng and body <= 0.35 * rng
    hit[0] = hammerShape and down
    hit[1] = hammerShape and upt
    hit[2] = invShape and down
    hit[3] = invShape and upt
    hit[4] = bear1 and bull0 and o <= c1 and c >= o1 and body > b1 and down
    hit[5] = bull1 and bear0 and o >= c1 and c <= o1 and body > b1 and upt
    hit[6] = bear1 and long1 and bull0 and o >= c1 and c <= o1 and body < 0.5 * b1 and down
    hit[7] = bull1 and long1 and bear0 and o <= c1 and c >= o1 and body < 0.5 * b1 and upt
    hit[8] = bear1 and long1 and bull0 and o <= c1 and c > (o1 + c1) / 2 and c < o1 and down
    hit[9] = bull1 and long1 and bear0 and o >= c1 and c < (o1 + c1) / 2 and c > o1 and upt
    star = _body(O, C, i + 1) <= 0.3 * b2
    hit[10] = bear2 and long2 and star and bull0 and c > (o2 + c2) / 2 and C[i + 3] < C[i + 8]
    hit[11] = bull2 and long2 and star and bear0 and c < (o2 + c2) / 2 and C[i + 3] > C[i + 8]
    s0 = bull0 and body > 0.6 * avg and up < 0.3 * body
    s1 = bull1 and b1 > 0.6 * avg and _up(O, H, C, i + 1) < 0.3 * b1
    s2 = bull2 and b2 > 0.6 * avg and _up(O, H, C, i + 2) < 0.3 * b2
    hit[12] = s0 and s1 and s2 and c > c1 and c1 > c2 and o > o1 and o < c1 and o1 > o2 and o1 < c2
    k0 = bear0 and body > 0.6 * avg and lo < 0.3 * body
    k1 = bear1 and b1 > 0.6 * avg and _lo(O, L, C, i + 1) < 0.3 * b1
    k2 = bear2 and b2 > 0.6 * avg and _lo(O, L, C, i + 2) < 0.3 * b2
    hit[13] = k0 and k1 and k2 and c < c1 and c1 < c2 and o < o1 and o > c1 and o1 < o2 and o1 > c2
    doji = body <= 0.1 * rng
    hit[14] = doji and down
    hit[15] = doji and upt


# --- :360-383 --------------------------------------------------------------------------------------------
@njit(cache=True)
def CPVote(O, H, L, C, i, trend, useTrend, enabled, minBody):
    hit = np.zeros(16, np.bool_)
    DetectPatterns(O, H, L, C, i, hit)
    v = 0
    for p in range(16):
        if hit[p] and enabled[p]:
            v += PATDIR[p]
    d = 1 if v > 0 else (-1 if v < 0 else 0)
    if d == 0:
        return 0
    if minBody > 0:
        avgR = 0.0
        for k in range(1, 21):
            avgR += H[i + k] - L[i + k]
        avgR /= 20.0
        if _body(O, C, i) < minBody * avgR:
            return 0
    if useTrend and d != trend:
        return 0
    return d


# --- :394-399 --------------------------------------------------------------------------------------------
@njit(cache=True)
def InSession(tod, on, sessFrom, sessTo):
    if not on:
        return True
    if sessFrom <= sessTo:
        return tod >= sessFrom and tod < sessTo
    return tod >= sessFrom or tod < sessTo


# --- MT5 timeseries emulation on the chronological M5 export ----------------------------------------------
@njit(cache=True)
def iBarShift_chrono(T5, t):
    """exact=false: chronological index of the bar with the largest open time <= t (-1 if none)."""
    return np.searchsorted(T5, t, side='right') - 1


# --- :403-417 --------------------------------------------------------------------------------------------
@njit(cache=True)
def M5Dir(t, mode, T5, O5, C5, E5):
    idx = iBarShift_chrono(T5, t - 1)            # int sh = iBarShift(_Symbol, PERIOD_M5, t - 1, false)
    if idx < 0:                                  # if(sh < 0) return 0;
        return 0
    if T5[idx] + 300 > t:                        # if(iTime(sh) + 300 > t) sh++;   (sh++ = one bar older)
        idx -= 1
    if mode == M5_CANDLE:
        if idx < 0:                              # iOpen/iClose beyond history return 0
            return 0
        o = O5[idx]; c = C5[idx]
        if o <= 0 or c <= 0:
            return 0
        return 1 if c > o else (-1 if c < o else 0)
    # CopyBuffer(hM5, 0, sh, 2, e): e[0] = bar sh+1 (older), e[1] = bar sh
    if idx - 1 < 0:
        return 0
    e0 = E5[idx - 1]; e1 = E5[idx]
    return 1 if e1 > e0 else (-1 if e1 < e0 else 0)


@njit(cache=True)
def mt5_ema(price, period):
    """MT5 iMA MODE_EMA (MovingAverages.mqh ExponentialMAOnBuffer): seed = first price, then recursion."""
    sf = 2.0 / (1.0 + period)
    out = np.empty(len(price))
    out[0] = price[0]
    for i in range(1, len(price)):
        out[i] = price[i] * sf + out[i - 1] * (1.0 - sf)
    return out


# --- OnTick :742-811 (signal part), bar by bar -----------------------------------------------------------
@njit(cache=True)
def run_ea(T, O, H, L, C, V, SPR, trend_chrono, window_bars, need_full,
           n, k, maru, pbMinBody, sfmult, qbk, h0, h1, cptrend, cpOn, cpMinBody,
           m5mode, m5fades, T5, O5, C5, E5,
           firstTod, lastTod, closeTod, sessOn, sessFrom, sessTo,
           pctTP, tpArr, maxPts, pt, modOn, ind_mode):
    """For every chronological bar p: the EA's r[] = CopyRates(M1, 1, window) taken on the first tick of the next bar,
    so r[0] = bar p; series index i = N-1-p, total = i + window.
    Returns (raw[N,4]  = sig[] after the M5 filter and the hours/session zeroing, i.e. what sigCount counts,
             take[N,4] = raw after the entry filter: fresh (next bar opens within 120 s of the signal bar's open,
                         first tick assumed at the bar open), 22:58 window, spread proxy = RECORDED spread (points)
                         of the next bar, both the point limit and the % of TP limit, exactly as the EA compares them.
             d5[N]     = M5Dir value used)."""
    N = len(T)
    raw = np.zeros((N, 4), np.int64)
    take = np.zeros((N, 4), np.int64)
    d5out = np.zeros(N, np.int64)
    for p in range(N):
        i = N - 1 - p
        total = min(N, i + window_bars)
        if need_full and total - i < window_bars:      # if(total < 1500) return;  (EA: CopyRates must return 1500)
            continue
        tr = trend_chrono[p]
        sig = np.zeros(4, np.int64)
        if modOn[0]: sig[0] = SigPullback(T, O, H, L, C, i, total, n, k, maru, pbMinBody, tr)
        if modOn[1]: sig[1] = SigSpikeFade(T, O, H, L, C, i, total, sfmult, SessionVWAP(T, H, L, C, V, i, total))
        if modOn[2]: sig[2] = SigQuarterFade(T, O, H, L, C, i, total, qbk, h0, h1)
        if modOn[3]: sig[3] = CPVote(O, H, L, C, i, tr, cptrend, cpOn, cpMinBody)
        if m5mode != M5_OFF:
            d5 = M5Dir(T[i] + 60, m5mode, T5, O5, C5, E5)
            d5out[p] = d5
            for m in range(4):
                if sig[m] != 0 and (m == 0 or m == 3 or m5fades) and sig[m] != d5:
                    sig[m] = 0
        tod = (T[i] % 86400) // 60
        inHours = tod >= firstTod and tod <= lastTod and InSession(tod, sessOn, sessFrom, sessTo)
        if not inHours:
            sig[:] = 0
        for m in range(4):
            raw[p, m] = sig[m]
        if p + 1 >= N:
            continue
        tnow = T[i - 1]                                  # first tick of the next existing bar, at its open (best case)
        if ind_mode:                                     # indicator :526  time[i-1] - time[i] > 60 -> continue; no 22:58 check
            window = (tnow - T[i]) <= 60
        else:                                            # EA :787-788
            fresh = (tnow - (T[i] + 60)) <= 60
            window = fresh and ((tnow % 86400) // 60) < closeTod
        sprPts = SPR[i - 1]                              # EA: SYMBOL_SPREAD / ask-bid at the first tick; indicator: spread[i-1]
        spreadOk = maxPts <= 0 or sprPts <= maxPts
        spr = sprPts * pt                                # indicator: spread[i-1] * _Point
        if window:
            for m in range(4):
                if sig[m] == 0:
                    continue
                if (not spreadOk) or (pctTP > 0 and spr > pctTP / 100.0 * tpArr[m] + pt / 2):
                    continue
                take[p, m] = sig[m]
    return raw, take, d5out
