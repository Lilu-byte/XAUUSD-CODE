"""Independent re-implementation of the Market Matrix (Zeiierman) series, written from the Pine source only
(uploaded .md, lines 254-600), NOT from mm.py.  Every function walks bars like Pine does: series are numpy
float arrays with NaN = na, x[k] = value k bars back.

Pine built-in semantics used (TradingView reference manual):
  ta.sma   : mean of last n values, na while any of them is na
  ta.ema   : alpha = 2/(n+1), seeded with ta.sma(src, n) on the first bar it exists (na before)
  ta.rma   : alpha = 1/n, same SMA seed (this is what ta.atr / ta.rsi use)
  ta.tr    : bar 0 (high[1] na) -> high - low, else max(h-l, |h-c[1]|, |l-c[1]|)
  ta.atr   : ta.rma(ta.tr, n)
  ta.rsi   : rma(max(x-x[1],0)) / rma(max(x[1]-x,0)); 100 if down-rma == 0
  ta.stdev : biased (divide by n)
  ta.percentile_nearest_rank(src, n, p): window of n values incl. current, sorted ascending,
             value at ordinal rank ceil(p/100 * n)  (na ignored)
"""
import numpy as np
from numba import njit

# script defaults (Pine lines 123-212)
RSI_LEN, RSI_MA = 14, 9
MACD_F, MACD_S, MACD_SIG = 12, 26, 9
RTI_LEN, RTI_SENS, RTI_SIG = 100, 95, 20
ASI_LB, ASI_TOP, ASI_BOT, ASI_MA = 15, 0.15, 0.15, 14
RNG_LEN, RNG_MULT = 50, 2.0
SW_LEN, VW_APT = 50, 20.0


@njit(cache=True)
def p_sma(src, n):
    out = np.full(len(src), np.nan)
    for i in range(n - 1, len(src)):
        s = 0.0; ok = True
        for k in range(n):
            v = src[i - k]
            if np.isnan(v):
                ok = False; break
            s += v
        if ok:
            out[i] = s / n
    return out


@njit(cache=True)
def _seeded(src, n, alpha):
    seed = p_sma(src, n)
    out = np.full(len(src), np.nan)
    prev = np.nan
    for i in range(len(src)):
        if np.isnan(prev):
            cur = seed[i]
        else:
            cur = alpha * src[i] + (1 - alpha) * prev
        out[i] = cur; prev = cur
    return out


def p_ema(src, n): return _seeded(np.asarray(src, float), n, 2.0 / (n + 1))
def p_rma(src, n): return _seeded(np.asarray(src, float), n, 1.0 / n)


def ema_first_value_seed(src, n):
    """Alternative reading of ta.ema (seed = first non-na source value), for a sensitivity check only."""
    src = np.asarray(src, float); a = 2.0 / (n + 1); out = np.full(len(src), np.nan); prev = np.nan
    for i in range(len(src)):
        if np.isnan(src[i]):
            continue
        prev = src[i] if np.isnan(prev) else a * src[i] + (1 - a) * prev
        out[i] = prev
    return out


def p_tr(h, l, c):
    tr = np.empty(len(c))
    tr[0] = h[0] - l[0]
    pc = c[:-1]
    tr[1:] = np.maximum(np.maximum(h[1:] - l[1:], np.abs(h[1:] - pc)), np.abs(l[1:] - pc))
    return tr


def p_atr(h, l, c, n): return p_rma(p_tr(h, l, c), n)


def p_rsi(x, n):
    x = np.asarray(x, float)
    u = np.full(len(x), np.nan); dn = np.full(len(x), np.nan)
    u[1:] = np.maximum(x[1:] - x[:-1], 0.0); dn[1:] = np.maximum(x[:-1] - x[1:], 0.0)
    ru, rd = p_rma(u, n), p_rma(dn, n)
    with np.errstate(divide='ignore', invalid='ignore'):
        r = 100.0 - 100.0 / (1.0 + ru / rd)
    r = np.where(rd == 0, 100.0, np.where(ru == 0, 0.0, r))
    r[np.isnan(ru) | np.isnan(rd)] = np.nan
    return r


@njit(cache=True)
def p_stdev(src, n):
    out = np.full(len(src), np.nan)
    for i in range(n - 1, len(src)):
        m = 0.0
        for k in range(n):
            m += src[i - k]
        m /= n
        ss = 0.0
        for k in range(n):
            dd = src[i - k] - m
            if abs(dd) <= 1e-10:
                dd = 0.0
            ss += dd * dd
        out[i] = np.sqrt(ss / n)
    return out


@njit(cache=True)
def p_pct_nearest_rank(src, n, p):
    out = np.full(len(src), np.nan)
    buf = np.empty(n)
    for i in range(n - 1, len(src)):
        m = 0
        for k in range(n):
            v = src[i - k]
            if not np.isnan(v):
                buf[m] = v; m += 1
        if m == 0:
            continue
        w = np.sort(buf[:m])
        rank = int(np.ceil(p / 100.0 * m))
        rank = max(1, min(m, rank))
        out[i] = w[rank - 1]
    return out


# ---------------- rti_calc (Pine 288-300) ----------------
def rti_calc(c):
    dev = p_stdev(c, 2)
    up, lo = c + dev, c - dev
    L, S = RTI_LEN, RTI_SENS
    ur = max(1, min(L, int(np.floor(S / 100.0 * L + 0.5))))          # math.round = half away from zero
    lr = max(1, min(L, int(np.floor((100.0 - S) / 100.0 * L + 0.5))))
    upct = (ur - 0.5) * 100.0 / L
    lpct = (lr - 0.5) * 100.0 / L
    hi = p_pct_nearest_rank(up, L, upct)
    lw = p_pct_nearest_rank(lo, L, lpct)
    n = len(c)
    res = np.full(n, np.nan)
    for i in range(n):
        if i - (L - 1) < 0:
            continue
        if np.isnan(up[i - (L - 1)]) or np.isnan(lo[i - (L - 1)]):
            continue
        if hi[i] != lw[i]:
            res[i] = 100.0 * (c[i] - lw[i]) / (hi[i] - lw[i])
    return res, p_ema(res, RTI_SIG), (ur, lr, upct, lpct)


# ---------------- asi_calc (Pine 303-327) ----------------
@njit(cache=True)
def _asi_value(c, lb, top, bot):
    n = len(c)
    val = np.zeros(n)
    widx = np.full(n, -1); lidx = np.full(n, -1); cnts = np.zeros(n, np.int64)
    buf = np.empty(lb)
    for t in range(n):
        m = 0
        for k in range(1, lb + 1):
            if t - k - 1 >= 0:                 # close[k] and close[k+1] exist (no na in data)
                ck = c[t - k]; ck1 = c[t - k - 1]
                if ck1 != 0:
                    buf[m] = ck / ck1 - 1.0; m += 1
        v = 0.0
        if m > 0:
            r = np.sort(buf[:m])
            wi = int(np.ceil(m * (1.0 - top))) - 1
            li = int(np.ceil(m * bot)) - 1
            wi = max(0, min(m - 1, wi)); li = max(0, min(m - 1, li))
            winner = r[wi]; loser = r[li]
            cur = np.nan
            if t - lb >= 0 and c[t - lb] != 0:
                cur = c[t] / c[t - lb] - 1.0
            if (not np.isnan(cur)) and winner != loser:
                v = (cur - loser) / (winner - loser) * 2.0 - 1.0
            widx[t] = wi; lidx[t] = li; cnts[t] = m
        val[t] = v
    return val, widx, lidx, cnts


def asi_calc(c):
    v, wi, li, cnt = _asi_value(c, ASI_LB, ASI_TOP, ASI_BOT)
    return v, p_sma(v, ASI_MA), wi, li, cnt


# ---------------- range_calc (Pine 329-364), value only ----------------
@njit(cache=True)
def _range_mean(c, L):
    n = len(c); mean = np.full(n, np.nan)
    for t in range(n):
        wp = 0.0; wt = 0.0
        for i in range(L):
            if t - i - 1 < 0:
                continue                         # close[i+1] is na
            prevC = c[t - i - 1]; currC = c[t - i]
            if prevC != 0:
                w = abs(currC - prevC) / prevC
                wp += currC * w; wt += w
        if wt != 0:
            mean[t] = wp / wt
    return mean


def range_calc(h, l, c, atr2000=None):
    a2000 = p_atr(h, l, c, 2000) if atr2000 is None else atr2000
    a200 = p_atr(h, l, c, 200)
    raw = np.where(np.isnan(a2000), a200, a2000)          # nz(ta.atr(2000), ta.atr(200))
    ratr = raw * RNG_MULT
    mean = _range_mean(c, RNG_LEN)
    ok = ~np.isnan(mean) & ~np.isnan(ratr) & (ratr != 0)
    osc = np.where(ok, 100.0 * (c - mean) / np.where(ok, ratr, 1.0), np.nan)
    return osc, mean, ratr


@njit(cache=True)
def window_rma_last(x, n, W):
    """For each t: ta.rma(x, n) evaluated on a request context that holds only the last W bars
    (calc_bars_count = W), i.e. bars [t-W+1, t]; value at its last bar.  If fewer than W bars exist the
    context starts at bar 0.  NaN if the context has fewer than n bars."""
    N = len(x); out = np.full(N, np.nan); a = 1.0 / n
    for t in range(N):
        s0 = max(0, t - W + 1)
        if t - s0 + 1 < n:
            continue
        acc = 0.0
        for k in range(s0, s0 + n):
            acc += x[k]
        v = acc / n
        for k in range(s0 + n, t + 1):
            v = a * x[k] + (1 - a) * v
        out[t] = v
    return out


def window_atr_last(h, l, c, n, W):
    """ta.atr(n) inside a calc_bars_count=W context ending at t.  The context's first bar has no high[1], so its
    true range is high-low."""
    N = len(c)
    trf = p_tr(h, l, c)
    hl = h - l
    out = np.full(N, np.nan)
    # tr inside the window = trf except at the window's first bar (= high-low there)
    res = _window_atr(trf, hl, n, W)
    return res


@njit(cache=True)
def _window_atr(trf, hl, n, W):
    N = len(trf); out = np.full(N, np.nan); a = 1.0 / n
    for t in range(N):
        s0 = max(0, t - W + 1)
        if t - s0 + 1 < n:
            continue
        acc = hl[s0]
        for k in range(s0 + 1, s0 + n):
            acc += trf[k]
        v = acc / n
        for k in range(s0 + n, t + 1):
            v = a * trf[k] + (1 - a) * v
        out[t] = v
    return out


# ---------------- swing_vwap (Pine 517-598), defaults vwAdapt=false ----------------
@njit(cache=True)
def swing_vwap_core(highs, lows, closes, vols, swLen, vwApt):
    count = len(closes)
    value = np.full(count, np.nan)
    directionAt = np.zeros(count, np.int64)
    anchors = np.full(count, -1, np.int64); aprice = np.full(count, np.nan)
    akind = np.zeros(count, np.int64); aconf = np.full(count, -1, np.int64); na_ = 0
    ph = np.nan; pl = np.nan; phIndex = -1; plIndex = -1; lastDirection = 0
    wp = np.nan; wv = np.nan
    apt = float(np.floor(max(5.0, min(300.0, vwApt)) + 0.5))      # math.round, vwAdapt=false
    alpha = 1.0 - np.exp(-np.log(2.0) / max(1.0, apt))
    for j in range(count):
        hj = highs[j]; lj = lows[j]; cj = closes[j]; volj = vols[j]
        newestHigh = not np.isnan(hj); newestLow = not np.isnan(lj)
        if newestHigh or newestLow:
            for k in range(max(0, j - swLen + 1), j + 1):
                hk = highs[k]; lk = lows[k]
                if (not np.isnan(hk)) and (not np.isnan(hj)) and hk > hj:
                    newestHigh = False
                if (not np.isnan(lk)) and (not np.isnan(lj)) and lk < lj:
                    newestLow = False
        if newestHigh:
            ph = hj; phIndex = j
        if newestLow:
            pl = lj; plIndex = j
        direction = 1 if phIndex > plIndex else -1
        switch = lastDirection != 0 and direction != lastDirection
        if switch:
            anchorIndex = plIndex if direction > 0 else phIndex
            anchorPrice = pl if direction > 0 else ph
            if anchorIndex >= 0 and not np.isnan(anchorPrice):
                anchors[na_] = anchorIndex; aprice[na_] = anchorPrice
                akind[na_] = -1 if direction > 0 else 1; aconf[na_] = j; na_ += 1
                av = vols[anchorIndex]
                if np.isnan(av):
                    av = 0.0
                wp = anchorPrice * av; wv = av
                for k in range(anchorIndex, j + 1):
                    v = vols[k]
                    if np.isnan(v):
                        v = 0.0
                    hc3 = (highs[k] + lows[k] + closes[k]) / 3.0
                    wp = (1.0 - alpha) * wp + alpha * hc3 * v
                    wv = (1.0 - alpha) * wv + alpha * v
                    value[k] = wp / wv if wv > 0 else np.nan
                    directionAt[k] = direction
        else:
            if not np.isnan(cj):
                hc3 = (hj + lj + cj) / 3.0
                vz = 0.0 if np.isnan(volj) else volj
                if np.isnan(wp):
                    wp = hc3 * vz; wv = vz
                wp = (1.0 - alpha) * wp + alpha * hc3 * vz
                wv = (1.0 - alpha) * wv + alpha * vz
                value[j] = wp / wv if wv > 0 else np.nan
                directionAt[j] = direction
        lastDirection = direction
    return value, directionAt, anchors[:na_], aprice[:na_], akind[:na_], aconf[:na_]


@njit(cache=True)
def swing_live_windowed(h, l, c, v, swLen, vwApt, W):
    """What the chart shows at its last bar t when the swing loop runs on only the last W bars
    (historyCount = min(ac.size()+1, 1050) in Pine line 954): value and direction at t."""
    N = len(c); val = np.full(N, np.nan); dr = np.zeros(N, np.int64)
    for t in range(N):
        s0 = max(0, t - W + 1)
        vv, dd, a, b, kk, cf = swing_vwap_core(h[s0:t + 1], l[s0:t + 1], c[s0:t + 1], v[s0:t + 1], swLen, vwApt)
        val[t] = vv[-1]; dr[t] = dd[-1]
    return val, dr


@njit(cache=True)
def swing_live_growing(h, l, c, v, swLen, vwApt, stride):
    """Brute force: rerun the whole loop on bars [0, t] for t = stride-1, 2*stride-1, ... and keep index t."""
    N = len(c); val = np.full(N, np.nan); dr = np.zeros(N, np.int64)
    for t in range(N):
        if t % stride != 0 and t != N - 1:
            continue
        vv, dd, a, b, kk, cf = swing_vwap_core(h[:t + 1], l[:t + 1], c[:t + 1], v[:t + 1], swLen, vwApt)
        val[t] = vv[-1]; dr[t] = dd[-1]
    return val, dr


def tags(aprice, akind):
    """HH/LH/HL/LL as in Pine 1064-1078 (compare with the previous anchor of the same kind)."""
    out = []; prevH = np.nan; prevL = np.nan
    for p, k in zip(aprice, akind):
        t = ''
        if k == 1:
            if not np.isnan(prevH):
                t = 'HH' if p > prevH else 'LH' if p < prevH else ''
            prevH = p
        elif k == -1:
            if not np.isnan(prevL):
                t = 'HL' if p > prevL else 'LL' if p < prevL else ''
            prevL = p
        out.append(t)
    return out


def all_series(d):
    h, l, c = d.high.values.astype(float), d.low.values.astype(float), d.close.values.astype(float)
    v = d.vol.values.astype(float)
    S = {}
    S['rsi'] = p_rsi(c, RSI_LEN); S['rsi_ma'] = p_sma(S['rsi'], RSI_MA)
    e1, e2 = p_ema(c, MACD_F), p_ema(c, MACD_S)
    S['macd'] = e1 - e2; S['macd_sig'] = p_ema(S['macd'], MACD_SIG); S['macd_hist'] = S['macd'] - S['macd_sig']
    S['rti'], S['rti_sig'], rti_par = rti_calc(c)
    S['asi'], S['asi_sig'], wi, li, cnt = asi_calc(c)
    S['rng'], S['rng_mean'], S['rng_atr'] = range_calc(h, l, c)
    S['ema89'] = p_ema(c, 89)
    S['sma20'], S['sma50'], S['sma200'] = p_sma(c, 20), p_sma(c, 50), p_sma(c, 200)
    vv, dd, an, ap, ak, ac = swing_vwap_core(h, l, c, v, SW_LEN, VW_APT)
    S['vwap_redrawn'], S['vw_dir_redrawn'] = vv, dd
    meta = dict(rti_par=rti_par, asi_wi=wi, asi_li=li, asi_cnt=cnt, anchors=(an, ap, ak, ac))
    return S, meta
