"""Classic candlestick patterns (standard textbook definitions, as in Investopedia's
candlestick primer). Each returns +1 (bullish signal), -1 (bearish) or 0 at the bar
that completes the pattern, using that bar and earlier bars only."""
import numpy as np, pandas as pd


def parts(d, n_avg=20, n_trend=6):
    o, h, l, c = d.open, d.high, d.low, d.close
    body = (c - o).abs(); rng = (h - l).replace(0, np.nan)
    up = h - np.maximum(o, c); lo = np.minimum(o, c) - l
    avg = body.rolling(n_avg).mean().shift(1)
    # prior trend: the close before the pattern vs n_trend bars earlier
    down = c.shift(1) < c.shift(n_trend); upt = c.shift(1) > c.shift(n_trend)
    return o, h, l, c, body, rng, up, lo, avg, down, upt


def detect(d):
    o, h, l, c, body, rng, up, lo, avg, down, upt = parts(d)
    bull, bear = c > o, c < o
    o1, c1, b1 = o.shift(1), c.shift(1), body.shift(1)
    o2, c2, b2 = o.shift(2), c.shift(2), body.shift(2)
    long1 = b1 > avg; long2 = b2 > avg
    hammer_shape = (lo >= 2 * body) & (up <= 0.5 * body + 0.05 * rng) & (body <= 0.35 * rng)
    inv_shape = (up >= 2 * body) & (lo <= 0.5 * body + 0.05 * rng) & (body <= 0.35 * rng)
    P = {}
    P['Hammer'] = (hammer_shape & down) * 1
    P['Hanging man'] = (hammer_shape & upt) * -1
    P['Inverted hammer'] = (inv_shape & down) * 1
    P['Shooting star'] = (inv_shape & upt) * -1
    P['Bullish engulfing'] = (bear.shift(1) & bull & (o <= c1) & (c >= o1) & (body > b1) & down) * 1
    P['Bearish engulfing'] = (bull.shift(1) & bear & (o >= c1) & (c <= o1) & (body > b1) & upt) * -1
    P['Bullish harami'] = (bear.shift(1) & long1 & bull & (o >= c1) & (c <= o1) & (body < 0.5 * b1) & down) * 1
    P['Bearish harami'] = (bull.shift(1) & long1 & bear & (o <= c1) & (c >= o1) & (body < 0.5 * b1) & upt) * -1
    P['Piercing line'] = (bear.shift(1) & long1 & bull & (o <= c1) & (c > (o1 + c1) / 2) & (c < o1) & down) * 1
    P['Dark cloud cover'] = (bull.shift(1) & long1 & bear & (o >= c1) & (c < (o1 + c1) / 2) & (c > o1) & upt) * -1
    star = body.shift(1) <= 0.3 * b2
    P['Morning star'] = (bear.shift(2) & long2 & star & bull & (c > (o2 + c2) / 2) & (c.shift(3) < c.shift(8))) * 1
    P['Evening star'] = (bull.shift(2) & long2 & star & bear & (c < (o2 + c2) / 2) & (c.shift(3) > c.shift(8))) * -1
    sold = lambda k: bull.shift(k) & (body.shift(k) > 0.6 * avg) & (up.shift(k) < 0.3 * body.shift(k))
    crow = lambda k: bear.shift(k) & (body.shift(k) > 0.6 * avg) & (lo.shift(k) < 0.3 * body.shift(k))
    P['Three white soldiers'] = (sold(0) & sold(1) & sold(2) & (c > c1) & (c1 > c2) & (o > o1) & (o < c1) & (o1 > o2) & (o1 < c2)) * 1
    P['Three black crows'] = (crow(0) & crow(1) & crow(2) & (c < c1) & (c1 < c2) & (o < o1) & (o > c1) & (o1 < o2) & (o1 > c2)) * -1
    doji = body <= 0.1 * rng
    P['Doji after fall'] = (doji & down) * 1
    P['Doji after rise'] = (doji & upt) * -1
    P = {k: v.fillna(0).astype(float) for k, v in P.items()}
    allp = sum(P.values())
    P['Any pattern (net vote)'] = np.sign(allp)
    return P


SPINNING_TOP = lambda d: ((d.close - d.open).abs() <= 0.3 * (d.high - d.low)) & ((d.high - np.maximum(d.open, d.close)) > (d.close - d.open).abs()) & ((np.minimum(d.open, d.close) - d.low) > (d.close - d.open).abs())
