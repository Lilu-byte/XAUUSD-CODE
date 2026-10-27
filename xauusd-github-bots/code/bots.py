"""Rebuilds of the GitHub bots, from the specs in ../specs/. Each function returns (data, signal, simulate-kwargs).
All bots trade one 0.01 lot ($1 per $1 move). Risk-% sizing in the originals is replaced by the fixed 0.01 lot
David runs; daily %-loss limits are therefore left out unless they are in dollars.
Author bugs that would stop a bot trading (BAKOME daily counter, GOLD_ORB drawdown flag) are fixed so the
intended logic is what gets tested.
"""
import numpy as np, pandas as pd
from gbt import load, htf, ema, sma, rma, atr, rsi, adx, stoch, macd, tod

S = 0.30  # spread used for cost gates


def xup(a, b): return (a > b) & (a.shift() <= b.shift())
def xdn(a, b): return (a < b) & (a.shift() >= b.shift())


# ---------------- maker-tung/xauusd-trend-follow (H1, long only) ----------------
def maker_tung(tf='H1'):
    d = load(tf); c = d.close
    a = atr(d, 14); ad, _, _ = adx(d, 14)
    m, ms = macd(c); k, dd = stoch(d, 5, 3, 3)
    trig = xup(m, ms) | (xup(k, dd) & (k < 60)) | xup(ema(c, 9), ema(c, 21))
    sig = ((c > ema(c, 200)) & (ad >= 20) & trig).astype(float)
    return d, sig, dict(sl=1.25 * a, tp=6.0 * a, max_bars=60)


# ---------------- yulz008/GOLD_ORB (H1 opening range breakout) ----------------
def gold_orb():
    d = load('H1'); O, H, L, C = (d[x].values for x in ('open', 'high', 'low', 'close'))
    hr = d.index.hour.values; n = len(d); sig = np.zeros(n)
    armed = True; init_next = False; Rset = False
    Rh = Rl = Bh = Bl = 0.0; cR = cS = 0; ldone = sdone = True
    for t in range(1, n - 1):
        p = t - 1
        # the decision at the open of bar t+1 uses closed bar t; emulate "bar t+1 open" with index t+1 hour
        hour = hr[t + 1]; p = t
        bh, bl = max(O[p], C[p]), min(O[p], C[p])
        if hour == 1 and armed:
            armed = False; init_next = True; Rset = False; ldone = sdone = False; continue
        if hour == 2: armed = True
        if init_next:
            Rh = Bh if (H[p] - bh) > 5 else H[p]; Rl = bl if (bl - L[p]) > 5 else L[p]
            Rh = H[p] if (H[p] - bh) <= 5 else bh; Bh, Bl = bh, bl
            cR = cS = 1; init_next = False; Rset = True; continue
        if not Rset: continue
        if 1 <= cR <= 3 and H[p] > Rh + 0.1 and bh > Bh + 0.1:
            Rh = bh if (H[p] - bh) > 5 else H[p]; Bh = bh; cR = 1
        else: cR += 1
        if 1 <= cS <= 3 and L[p] < Rl - 0.1 and bl < Bl - 0.1:
            Rl = bl if (bl - L[p]) > 5 else L[p]; Bl = bl; cS = 1
        else: cS += 1
        if cR > 3 and C[p] > O[p] and C[p] > Rh and not ldone: sig[p] = 1; ldone = True
        elif cS > 3 and C[p] < O[p] and C[p] < Rl and not sdone: sig[p] = -1; sdone = True
    return d, sig, dict(sl=4.0, tp=12.0, trail_start=1.0, trail_dist=7.0, trail_step=0.10)


# ---------------- Maxi0-912 breakout + RSI (H1) ----------------
def maxi(N=40, ob=75, os_=25, k=2.0, rr=2.0):
    d = load('H1'); c = d.close
    dd = c.diff(); r = 100 - 100 / (1 + dd.clip(lower=0).rolling(14).mean() / (-dd).clip(lower=0).rolling(14).mean())
    a = atr(d, 14); q = a.rolling(500).quantile(0.30)
    hh = d.high.shift().rolling(N).max(); ll = d.low.shift().rolling(N).min(); e = ema(c, 200)
    ok = a >= q
    sig = np.where(ok & (c > hh) & (c > e) & (r < ob), 1, np.where(ok & (c < ll) & (c < e) & (r > os_), -1, 0))
    return d, sig, dict(sl=k * a, tp=rr * k * a)


# ---------------- ronnisnai-frog GoldReversionGuard (M5 z-score) ----------------
def zscore_mr(tf='M5', n=50, ez=2.2, xz=0.3, adx_max=22, rlo=0.5, rhi=2.0, slmin=5.0, h1filter=False,
              start=10, end=20, cool=6, max_day=8, be_off=0.20, hold=40, tp_floor=0.0):
    d = load(tf); c = d.close
    m = sma(c, n); s = c.rolling(n).std(ddof=0); z = (c - m) / s
    a = atr(d, 14); ratio = a / a.rolling(50).mean(); ad, _, _ = adx(d, 14)
    hr = d.index.hour
    ok = (hr >= start) & (hr < end) & ~((d.index.dayofweek == 4) & (hr >= 20)) & (ad <= adx_max) & \
         (ratio >= rlo) & (ratio <= rhi) & (s >= 3 * S) & ((m - c).abs() >= 4 * S)
    if h1filter:
        h1 = load('H1'); hs = htf(d, 'H1', sma(h1.close, 50).values)
        okl = ok & (c > hs); oks = ok & (c < hs)
    else:
        okl = oks = ok
    sig = np.where(okl & (z <= -ez) & (c >= c.shift()), 1, np.where(oks & (z >= ez) & (c <= c.shift()), -1, 0))
    sld = np.maximum(slmin, 2.5 * a)
    tpd = (m - c).abs()
    return d, sig, dict(sl=sld, tp=tpd, exit_long=(z >= -xz).values, exit_short=(z <= xz).values, max_bars=hold,
                        be_trig=a, be_off=be_off, cooldown=cool, max_day=max_day, fri_eod=20 * 60,
                        tp_track_long=m.values, tp_track_short=m.values, tp_floor=tp_floor)


def n30_tickrobust(tf='M1'):
    return zscore_mr(tf, n=20, ez=2.2, xz=0.2, rlo=0.4, slmin=8.0, h1filter=True, cool=15 if tf == 'M1' else 3,
                     max_day=0, be_off=S + 0.02, tp_floor=S + 0.05)


# ---------------- Sandyyy123 scalper (M5) ----------------
def sandyyy(tf='M5'):
    d = load(tf); c = d.close; a = atr(d, 14); r = rsi(c, 7); k, dd = stoch(d, 5, 3, 3)
    e20, e50 = ema(c, 20), ema(c, 50); hr = d.index.hour; ses = (hr >= 7) & (hr < 17)
    sig = np.where(ses & (e20 > e50) & (r < 30) & (k < 20) & (k > dd), 1,
                   np.where(ses & (e20 < e50) & (r > 70) & (k > 80) & (k < dd), -1, 0))
    return d, sig, dict(sl=a, tp=1.5 * a)


# ---------------- Bongo-Seakhoa DayTradingEA_v2 (BB mean reversion) ----------------
def bongo(tf='M5'):
    d = load(tf); O, H, L, C = d.open, d.high, d.low, d.close
    mid = sma(C, 20); sd = C.rolling(20).std(ddof=0); up, lo = mid + 2 * sd, mid - 2 * sd
    e = ema(C, 20); r = rsi(C, 14); a = atr(d, 14)
    body = (C - O).abs(); rng = H - L
    lw = np.minimum(O, C) - L; uw = H - np.maximum(O, C)
    hammer = (lw > 2 * body) & (uw < 0.5 * body) & (body > 0.1 * rng)
    star = (uw > 2 * body) & (lw < 0.5 * body) & (body > 0.1 * rng)
    beng = (C.shift() < O.shift()) & (C > O) & (C > O.shift()) & (O < C.shift())
    seng = (C.shift() > O.shift()) & (C < O) & (C < O.shift()) & (O > C.shift())
    # bar index k back = shift(k-1) relative to the closed bar (bar 1)
    C2, C3, C4, L2, H2 = C.shift(1), C.shift(2), C.shift(3), L.shift(1), H.shift(1)
    buy = ((C2 < lo) | (L2 < lo)) & (C4 < e) & (C3 < e) & (C4 > C3) & (C3 > C2) & (r < 40) & (hammer | beng)
    sell = ((C2 > up) | (H2 > up)) & (C4 > e) & (C3 > e) & (C4 < C3) & (C3 < C2) & (r > 60) & (star | seng)
    hr = d.index.hour.values; ses = (hr >= 7) & (hr < 20) & ~((d.index.dayofweek.values == 4) & (hr >= 20))
    b, s_, Cv, lov, midv, upv = buy.values, sell.values, C.values, lo.values, mid.values, up.values
    sig = np.zeros(len(d)); pend = 0; left = 0; pl = pm = pu = 0.0
    for i in range(len(d)):
        if not ses[i]: pend = 0; continue
        if pend:
            left -= 1
            if pend == 1 and pl < Cv[i] < pm: sig[i] = 1; pend = 0
            elif pend == -1 and pm < Cv[i] < pu: sig[i] = -1; pend = 0
            elif left <= 0: pend = 0
            continue
        if b[i]:
            if lov[i] < C2.values[i] < midv[i]: sig[i] = 1
            else: pend, left, pl, pm, pu = 1, 2, lov[i], midv[i], upv[i]
        elif s_[i]:
            if midv[i] < C2.values[i] < upv[i]: sig[i] = -1
            else: pend, left, pl, pm, pu = -1, 2, lov[i], midv[i], upv[i]
    # trailing levels decided on closed bars
    fibs = [0.236, 0.382, 0.5, 0.618]
    tl = np.where(C >= e, e, 0.0)
    for f in fibs:
        x = e + f * (up - e); tl = np.where(C >= x, np.maximum(tl, x), tl)
    ts = np.where(C <= e, e, 0.0)
    for f in fibs:
        x = e - f * (e - lo); ts = np.where(C <= x, np.where(ts == 0, x, np.minimum(ts, x)), ts)
    return d, sig, dict(sl=2 * a, tp=(up - C).abs().where(pd.Series(sig, index=d.index) > 0, (C - lo).abs()).values,
                        be_trig=2 * a, be_off=0.02, sl_track_long=tl, sl_track_short=ts,
                        tp_track_long=up.values, tp_track_short=lo.values, tp_expand=True)


# ---------------- BAKOME "ICT" scalper (M5) ----------------
def bakome():
    d = load('M5'); c = d.close; a = atr(d, 14)
    h4 = load('H4'); be = htf(d, 'H4', ema(h4.close, 200).values)
    nxt_hr = pd.Series(d.index.hour, index=d.index).shift(-1)
    win = nxt_hr.isin([8, 15]) & (a >= 1.0)
    sig = np.where(win & (c > be), 1, np.where(win & (c < be), -1, 0))
    return d, sig, dict(sl=2 * a, tp=3 * a, trail_start=1.5 * a, trail_dist=0.5 * a, max_day=10)


# ---------------- phatnomenal blackXAU (M5, long only, prev-day-high retest) ----------------
def blackxau():
    d = load('M5'); O, H, L, C = (d[x].values for x in ('open', 'high', 'low', 'close'))
    D = load('D1'); zh = htf(d, 'D1', D.high.values)
    h1 = load('H1'); e50 = htf(d, 'H1', ema(h1.close, 50).values); e200 = htf(d, 'H1', ema(h1.close, 200).values)
    a1 = htf(d, 'H1', atr(h1, 14).values)
    hr = d.index.hour.values; t = d.index.values; n = len(d)
    sig = np.zeros(n); sld = np.zeros(n); tpd = np.zeros(n)
    setup = 0; t0 = None; zl = htf(d, 'D1', D.low.values)
    for i in range(1, n - 1):
        nh = hr[i + 1]
        if not (7 <= nh <= 22): continue
        body = abs(C[i] - O[i]); rg = H[i] - L[i]
        strong = body >= 0.5 * rg or body >= 2.0
        if C[i] > zh[i] and O[i] <= zh[i] and strong: setup, t0 = 1, t[i]
        elif C[i] < zl[i] and O[i] >= zl[i] and strong: setup = 0
        if setup == 1 and (t[i] - t0) > np.timedelta64(1, 'D'): setup = 0
        if setup == 1 and C[i] > e50[i] and C[i] > e200[i] and C[i] <= zh[i]:
            fill = C[i] + 0.40; slv = zh[i] - 1.5 * a1[i]; tpv = zh[i] + 3 * a1[i]
            if fill - slv > 0 and tpv > fill:
                sig[i] = 1; sld[i] = fill - slv; tpd[i] = tpv - fill
            setup = 0
    return d, sig, dict(sl=sld, tp=tpd, trail_start=2.0, trail_dist=1.0, trail_step=0.01)


# ---------------- ilahuerta-IA "Sunrise Ogle" pullback window (M5, long only) ----------------
def ilahuerta(tf='M5', atr_cap=2.0):
    d = load(tf); O, H, L, C = (d[x].values for x in ('open', 'high', 'low', 'close'))
    c = d.close; e14, e24, e100 = ema(c, 14).values, ema(c, 24).values, ema(c, 100).values
    a = rma(pd.concat([d.high - d.low, (d.high - c.shift()).abs(), (d.low - c.shift()).abs()], axis=1).max(axis=1), 10).values
    n = len(d); sig = np.zeros(n); sld = np.zeros(n); tpd = np.zeros(n)
    st = 0; cnt = 0; top = bot = 0.0; wb = 0
    for t in range(1, n):
        if st == 0:
            x = (C[t] > e14[t] and C[t - 1] <= e14[t - 1]) or (C[t] > e24[t] and C[t - 1] <= e24[t - 1])
            if x and C[t] > e100[t] and a[t] <= atr_cap: st = 1; cnt = 0
        elif st == 1:
            if C[t] < O[t]:
                cnt += 1
                if cnt == 3:
                    r = H[t] - L[t]; top = H[t] + .001 * r; bot = L[t] - .001 * r; wb = t + 1; st = 2
            else: st = 0
        elif st == 2:
            if t > wb: st = 1; cnt = 0
            elif H[t] >= top:
                if C[t] > e100[t]:
                    fill = C[t] + 0.4
                    sig[t] = 1; sld[t] = fill - (L[t] - 4.5 * a[t]); tpd[t] = (H[t] + 6.5 * a[t]) - fill
                st = 0
            elif L[t] <= bot: st = 1; cnt = 0
    return d, sig, dict(sl=sld, tp=tpd)


# ---------------- Rithick574 EMA 21/55 + ADX (M15) ----------------
def rithick(tf='M15'):
    d = load(tf); c = d.close
    a = atr(d, 14, 'wilder')
    up = d.high.diff(); dn = -d.low.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=d.index); mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=d.index)
    tr = a * 0 + pd.concat([d.high - d.low, (d.high - c.shift()).abs(), (d.low - c.shift()).abs()], axis=1).max(axis=1)
    trs = rma(tr, 14); pdi = 100 * rma(pdm, 14) / trs; mdi = 100 * rma(mdm, 14) / trs
    ad = rma(100 * (pdi - mdi).abs() / (pdi + mdi), 14)
    f, s = ema(c, 21), ema(c, 55)
    sig = np.where(xup(f, s) & (ad > 20), 1, np.where(xdn(f, s) & (ad > 20), -1, 0))
    rev = np.where(xup(f, s), 1, np.where(xdn(f, s), -1, 0))
    return d, sig, dict(sl=2 * a, tp=3 * a, exit_long=rev == -1, exit_short=rev == 1)


# ---------------- zero-was-here Donchian 120/60 benchmark (H1) ----------------
def donchian(tf='H1', ent=120, ex=60):
    d = load(tf); a = atr(d, 48)
    hh = d.high.shift().rolling(ent).max(); ll = d.low.shift().rolling(ent).min()
    xh = d.high.shift().rolling(ex).max(); xl = d.low.shift().rolling(ex).min()
    sig = np.where(d.close > hh, 1, np.where(d.close < ll, -1, 0))
    return d, sig, dict(sl=2.5 * a, exit_long=(d.close < xl).values, exit_short=(d.close > xh).values)


REGISTRY = {
    'maker-tung TrendFollow (H1, long only)': maker_tung,
    'GOLD_ORB opening range (H1)': gold_orb,
    'Maxi0-912 breakout+RSI (H1)': maxi,
    'zero-was-here Donchian 120/60 (H1)': donchian,
    'Rithick574 EMA21/55+ADX (M15)': rithick,
    'GoldReversionGuard z-score (M5)': zscore_mr,
    'GoldReversionGuard z-score (M15)': lambda: zscore_mr('M15'),
    'n30 TickRobust z-score (M1)': n30_tickrobust,
    'n30 TickRobust z-score (M5)': lambda: n30_tickrobust('M5'),
    'Sandyyy123 "75%" scalper (M5)': sandyyy,
    'Bongo BB reversion (M5)': bongo,
    'Bongo BB reversion (M15)': lambda: bongo('M15'),
    'BAKOME "ICT" scalper (M5)': bakome,
    'blackXAU prev-day-high retest (M5, long)': blackxau,
    'ilahuerta pullback window (M5, long)': ilahuerta,
}

# ---- relaxed variants: give the idea a fair chance when a faithful filter blocks nearly every trade ----
REGISTRY.update({
    'GoldReversionGuard, no ADX filter (M5)': lambda: zscore_mr('M5', adx_max=1e9),
    'GoldReversionGuard, no ADX filter (M15)': lambda: zscore_mr('M15', adx_max=1e9),
    'n30 TickRobust, no ADX filter (M1)': lambda: (lambda d, s, k: (d, s, k))(*_n30_noadx()),
    'ilahuerta, ATR cap scaled to price (M5)': lambda: ilahuerta('M5', atr_cap=4.0),
})


def _n30_noadx():
    return zscore_mr('M1', n=20, ez=2.2, xz=0.2, rlo=0.4, slmin=8.0, h1filter=True, cool=15, max_day=0,
                     be_off=S + 0.02, tp_floor=S + 0.05, adx_max=1e9)
