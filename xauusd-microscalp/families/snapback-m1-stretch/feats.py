"""snapback-m1-stretch: causal features and fade signals on M1 (decided at the close of bar i, bars <= i only).

Notation at a closed M1 bar i: O, H, L, C, tick volume V.
  A      = mean(H - L) over the last 240 M1 bars including i            ("ATR240", simple mean of bar ranges)
  cloc   = (C - L) / (H - L)                                            (0.5 when H == L)
  z_n    = (C - SMA_n(C)) / STDpop_n(C)        over the last n closes including C
  RSI_n  = Wilder RSI(n) of closes (alpha = 1/n smoothing of up/down moves)
  VWAP   = sum(TP*V)/sum(V) over the server day so far (TP = (H+L+C)/3), reset at the first bar of each day
  EMA50  = exponential MA of closes, alpha = 2/51
  streak = signed count of consecutive same-colour bars ending at i (C>O: +, C<O: -, doji ends a run -> 0)
  runmv  = C[i] - O[first bar of that run]
  forming M5 (clock-aligned 5-minute candle the bar i belongs to, as known at the close of i):
           fbody = C[i] - open of the forming M5 candle
           A5    = mean(high - low) of the 12 CLOSED M5 candles before the forming one
  r3     = C[i] - C[i-3]   (used only for the plain 3-bar spike fade, which this family does not tune)
Every signal returned by `signals` is the direction to TRADE (+1 buy, -1 sell), i.e. already a fade.
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import load_m1, resample, SPLIT

sg = lambda x: np.sign(np.nan_to_num(np.asarray(x, float)))


def features(m):
    f = pd.DataFrame(index=m.index)
    O, H, L, C, V = m.open, m.high, m.low, m.close, m.tick_volume
    rng = H - L
    f['A'] = rng.rolling(240).mean()
    f['rng'] = rng
    f['cloc'] = np.where(rng > 0, (C - L) / rng.where(rng > 0, 1.0), 0.5)
    f['body'] = C - O
    for n in (20, 30, 60):
        mu = C.rolling(n).mean(); sd = C.rolling(n).std(ddof=0)
        f[f'z{n}'] = (C - mu) / sd.where(sd > 0)
    d = C.diff()
    for n in (2, 3):
        up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
        dn = (-d).clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
        f[f'rsi{n}'] = 100 * up / (up + dn).where((up + dn) > 0)
    day = m.index.normalize()
    tp = (H + L + C) / 3
    vw = (tp * V).groupby(day).cumsum() / V.groupby(day).cumsum()
    f['vwd'] = C - vw
    f['emad'] = C - C.ewm(span=50, adjust=False).mean()
    col = np.sign(C - O).values
    st = np.zeros(len(C)); first = np.zeros(len(C), np.int64)
    for i in range(len(C)):
        if col[i] != 0 and i > 0 and np.sign(st[i - 1]) == col[i]:
            st[i] = st[i - 1] + col[i]; first[i] = first[i - 1]
        else:
            st[i] = col[i]; first[i] = i
    f['streak'] = st
    f['runmv'] = C.values - O.values[first]
    m5 = resample(m, 5)
    a5 = (m5.high - m5.low).rolling(12).mean().shift(1)          # 12 closed M5 candles before this one
    key = m.index.floor('5min')
    f['A5'] = a5.reindex(key).values
    g = m.groupby(key)
    f['fbody'] = C - g.open.transform('first')
    f['fmin'] = g.cumcount().values + 1
    f['r3'] = C - C.shift(3)
    return f


def sig_rexp(f, k, q):
    """range-expansion bar: H-L > k*A and close in the top q of the bar -> sell; bottom q -> buy"""
    big = f.rng.values > k * f.A.values
    return np.where(big & (f.cloc.values >= 1 - q), -1, np.where(big & (f.cloc.values <= q), 1, 0)).astype(float)


def sig_z(f, n, th):
    z = f[f'z{n}'].values
    return np.where(z > th, -1, np.where(z < -th, 1, 0)).astype(float)


def sig_rsi(f, n, th):
    x = f[f'rsi{n}'].values
    return np.where(x > th, -1, np.where(x < 100 - th, 1, 0)).astype(float)


def sig_vwap(f, k):
    x = f.vwd.values / f.A.values
    return np.where(x > k, -1, np.where(x < -k, 1, 0)).astype(float)


def sig_ema(f, k):
    x = f.emad.values / f.A.values
    return np.where(x > k, -1, np.where(x < -k, 1, 0)).astype(float)


def sig_run(f, mlen, k):
    st = f.streak.values; mv = f.runmv.values; a = f.A.values
    up = (st >= mlen) & (mv > k * a); dn = (st <= -mlen) & (mv < -k * a)
    return np.where(up, -1, np.where(dn, 1, 0)).astype(float)


def sig_fm5(f, k):
    x = f.fbody.values / f.A5.values
    return np.where(x > k, -1, np.where(x < -k, 1, 0)).astype(float)


def sig_spike3(f, k=3.0, usd=6.0):
    """the plain 3-bar spike fade (reference only, NOT tuned here): |C - C[i-3]| > k*A or > $usd"""
    r = f.r3.values
    hit = (np.abs(r) > k * f.A.values) | (np.abs(r) > usd)
    return np.where(hit, -sg(r), 0).astype(float)


def valid(m, f):
    return (np.isfinite(f.A.values) & np.isfinite(f.A5.values) & np.isfinite(f.z60.values)).astype(bool)


def singles(f):
    S = {}
    for k in (2, 2.5, 3, 4):
        for q in (0.2, 0.33): S[f'rexp{k}_q{q}'] = sig_rexp(f, k, q)
    for n in (20, 30, 60):
        for th in (2, 2.5, 3, 3.5): S[f'z{n}_{th}'] = sig_z(f, n, th)
    for n in (2, 3):
        for th in (95, 97.5, 99): S[f'rsi{n}_{th}'] = sig_rsi(f, n, th)
    for k in (4, 6, 8, 12): S[f'vwap{k}a'] = sig_vwap(f, k)
    for k in (2, 3, 4, 6): S[f'ema{k}a'] = sig_ema(f, k)
    for ml in (4, 5, 6):
        for k in (2, 3, 4): S[f'run{ml}_{k}a'] = sig_run(f, ml, k)
    for k in (1.0, 1.5, 2.0, 2.5): S[f'fm5_{k}'] = sig_fm5(f, k)
    return S


def both(a, b):
    """two conditions agreeing on the fade direction"""
    return np.where((a != 0) & (a == b), a, 0).astype(float)


def union(a, b):
    """either trigger; a wins where both fire (they cannot disagree in sign when both are fades of the same stretch,
    and when they do, a is kept)"""
    return np.where(a != 0, a, b).astype(float)
