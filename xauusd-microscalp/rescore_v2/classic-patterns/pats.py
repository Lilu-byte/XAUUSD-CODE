"""Classic candlestick patterns on k-minute candles, mapped onto the M1 timeline without look-ahead.

Extends /mnt/project-files/xauusd-candles/code/patterns.py (same textbook definitions) with
marubozu, tweezer top/bottom and spinning top. Each pattern is +1 (textbook bullish), -1 (textbook
bearish) or 0 at the candle that COMPLETES it, using that candle and earlier candles only.

k-minute candles: resample(m1, k) with phase offset p (bucket starts at minutes = p mod k).
A bucket labelled t (open time) is complete at t+k, i.e. at the close of the M1 bar indexed t+k-1;
the signal is placed on exactly that M1 row (entry at its close). 'rolling' = union of all k phases,
i.e. at every M1 close, the pattern on the k-minute candles ending at that close.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *


def detect_ext(d, n_avg=20, n_trend=6):
    o, h, l, c = d.open, d.high, d.low, d.close
    body = (c - o).abs(); rng = (h - l).replace(0, np.nan)
    up = h - np.maximum(o, c); lo = np.minimum(o, c) - l
    avg = body.rolling(n_avg).mean().shift(1)
    avgr = (h - l).rolling(n_avg).mean().shift(1)
    down = c.shift(1) < c.shift(n_trend); upt = c.shift(1) > c.shift(n_trend)
    bull, bear = c > o, c < o
    o1, c1, b1, h1, l1 = o.shift(1), c.shift(1), body.shift(1), h.shift(1), l.shift(1)
    o2, c2, b2 = o.shift(2), c.shift(2), body.shift(2)
    long1 = b1 > avg; long2 = b2 > avg
    hammer_shape = (lo >= 2 * body) & (up <= 0.5 * body + 0.05 * rng) & (body <= 0.35 * rng)
    inv_shape = (up >= 2 * body) & (lo <= 0.5 * body + 0.05 * rng) & (body <= 0.35 * rng)
    P = {}
    P['hammer'] = (hammer_shape & down) * 1
    P['hanging_man'] = (hammer_shape & upt) * -1
    P['inv_hammer'] = (inv_shape & down) * 1
    P['shooting_star'] = (inv_shape & upt) * -1
    P['bull_engulf'] = (bear.shift(1) & bull & (o <= c1) & (c >= o1) & (body > b1) & down) * 1
    P['bear_engulf'] = (bull.shift(1) & bear & (o >= c1) & (c <= o1) & (body > b1) & upt) * -1
    P['bull_harami'] = (bear.shift(1) & long1 & bull & (o >= c1) & (c <= o1) & (body < 0.5 * b1) & down) * 1
    P['bear_harami'] = (bull.shift(1) & long1 & bear & (o <= c1) & (c >= o1) & (body < 0.5 * b1) & upt) * -1
    P['piercing'] = (bear.shift(1) & long1 & bull & (o <= c1) & (c > (o1 + c1) / 2) & (c < o1) & down) * 1
    P['dark_cloud'] = (bull.shift(1) & long1 & bear & (o >= c1) & (c < (o1 + c1) / 2) & (c > o1) & upt) * -1
    star = body.shift(1) <= 0.3 * b2
    P['morning_star'] = (bear.shift(2) & long2 & star & bull & (c > (o2 + c2) / 2) & (c.shift(3) < c.shift(8))) * 1
    P['evening_star'] = (bull.shift(2) & long2 & star & bear & (c < (o2 + c2) / 2) & (c.shift(3) > c.shift(8))) * -1
    sold = lambda k: bull.shift(k) & (body.shift(k) > 0.6 * avg) & (up.shift(k) < 0.3 * body.shift(k))
    crow = lambda k: bear.shift(k) & (body.shift(k) > 0.6 * avg) & (lo.shift(k) < 0.3 * body.shift(k))
    P['three_soldiers'] = (sold(0) & sold(1) & sold(2) & (c > c1) & (c1 > c2) & (o > o1) & (o < c1) & (o1 > o2) & (o1 < c2)) * 1
    P['three_crows'] = (crow(0) & crow(1) & crow(2) & (c < c1) & (c1 < c2) & (o < o1) & (o > c1) & (o1 < o2) & (o1 > c2)) * -1
    doji = body <= 0.1 * rng
    P['doji_after_fall'] = (doji & down) * 1
    P['doji_after_rise'] = (doji & upt) * -1
    # additions
    maru = (body >= 0.9 * rng) & (body > avg)
    P['bull_marubozu'] = (maru & bull) * 1
    P['bear_marubozu'] = (maru & bear) * -1
    tol = 0.05 * avgr
    P['tweezer_bottom'] = (bear.shift(1) & bull & ((l - l1).abs() <= tol) & down) * 1
    P['tweezer_top'] = (bull.shift(1) & bear & ((h - h1).abs() <= tol) & upt) * -1
    spin = (body <= 0.3 * rng) & (up > body) & (lo > body)
    P['spin_after_fall'] = (spin & down) * 1
    P['spin_after_rise'] = (spin & upt) * -1
    P = {k: v.fillna(0).astype(float) for k, v in P.items()}
    return P


REV = ['hammer', 'hanging_man', 'inv_hammer', 'shooting_star', 'bull_engulf', 'bear_engulf', 'bull_harami',
       'bear_harami', 'piercing', 'dark_cloud', 'morning_star', 'evening_star', 'doji_after_fall',
       'doji_after_rise', 'tweezer_bottom', 'tweezer_top', 'spin_after_fall', 'spin_after_rise']
CONT = ['three_soldiers', 'three_crows', 'bull_marubozu', 'bear_marubozu']


def add_votes(P):
    """Vote signals: sign of the summed textbook directions; counts for threshold votes."""
    s_all = sum(P[k] for k in REV + CONT)
    s_rev = sum(P[k] for k in REV)
    s_strong = sum(P[k] for k in REV if not k.startswith(('doji', 'spin')))
    V = dict(P)
    V['vote_all'] = np.sign(s_all)
    V['vote_all_ge2'] = np.sign(s_all) * (s_all.abs() >= 2)
    V['vote_rev'] = np.sign(s_rev)
    V['vote_strong'] = np.sign(s_strong)
    V['vote_cont'] = np.sign(sum(P[k] for k in CONT))
    return V


def on_m1(m1, k, phase_mode='rolling', n_trend=6):
    """Dict pattern -> np.array on M1 rows (signal at the M1 close that completes the k-min candle)."""
    if k == 1:
        P = add_votes(detect_ext(m1[['open', 'high', 'low', 'close']], n_trend=n_trend))
        return {n: v.values for n, v in P.items()}
    phases = range(k) if phase_mode == 'rolling' else [0]
    out = None
    pos = pd.Series(np.arange(len(m1)), index=m1.index)
    for p in phases:
        d = m1.resample(f'{k}min', label='left', closed='left', offset=f'{p}min').agg(
            {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
        P = add_votes(detect_ext(d, n_trend=n_trend))
        end = d.index + pd.Timedelta(minutes=k - 1)        # M1 row whose close completes the candle
        rows = pos.reindex(end).values                       # NaN if that minute is missing
        ok = ~np.isnan(rows)
        rows = rows[ok].astype(int)
        if out is None: out = {n: np.zeros(len(m1)) for n in P}
        for n, v in P.items():
            out[n][rows] = v.values[ok]
    return out


def trend(m1, tf, fast=20, slow=80):
    """+1/-1: EMA fast vs slow on CLOSED tf bars, mapped to M1 rows without look-ahead."""
    d = load(tf)
    v = np.sign(ema(d.close, fast) - ema(d.close, slow)).values
    return np.nan_to_num(htf_on_m1(m1, d, tf, v).values)
