"""TRAIN only. Is the 'strong candle closing at its extreme -> fade' effect about the clock-aligned
forming candle (minute-in-candle) or a generic rolling-window effect? Bull vs bear split too."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from feats import *

m1 = load_m1(); X = build(m1); F = fwd(m1)
TR = X.train.values; ND = len(np.unique(m1.index[TR].date))
c = m1.close.values; tod = m1.tod.values


def stat(msk, d, ks=(1, 2, 3, 5)):
    msk = msk & TR
    r = dict(n_day=msk.sum() / ND, spr=X.spr.values[msk].mean())
    for k in ks: r[f'mv{k}'] = np.nanmean(F[k][msk] * d[msk])
    return r


def strong(o, h, l, cc, ar, thr, cl):
    rg = h - l; bn = (cc - o) / ar
    clv = np.where(rg > 0, (cc - l) / np.where(rg > 0, rg, 1), .5)
    bull = (bn > thr) & (clv >= cl); bear = (bn < -thr) & (clv <= 1 - cl)
    return bull, bear


pd.set_option('display.width', 250)
for p, mins in (('f15', range(1, 16)), ('f5', range(1, 6))):
    rows = []
    o, h, l, cc, mm = (X[p + k].values for k in 'ohlcm'); ar = X[p + 'ar12'].values
    bull, bear = strong(o, h, l, cc, ar, 0.6, 0.9)
    for m in mins:
        M = mm == m
        r = dict(minute=m); r.update({'all_' + k: v for k, v in stat(M & (bull | bear), np.where(bull, -1, 1)).items()})
        rb = stat(M & bull, -np.ones(len(c))); rs = stat(M & bear, np.ones(len(c)))
        r['bull_n'] = rb['n_day']; r['bull_mv3'] = rb['mv3']; r['bear_n'] = rs['n_day']; r['bear_mv3'] = rs['mv3']
        rows.append(r)
    print(f'\n{p} forming, body>0.6*ar12 & close in top/bottom 10% -> FADE (positive = fade pays)')
    print(pd.DataFrame(rows).round(3).to_string(index=False))

# rolling (not clock-aligned) 15-bar and 5-bar windows, broken down by minute-of-quarter
s = m1
for W in (15, 5):
    o = s.open.shift(W - 1).values; h = s.high.rolling(W).max().values; l = s.low.rolling(W).min().values
    rng = (s.high - s.low)
    # average W-bar range proxy: mean of rolling W-range over the previous 12*W bars
    rr = pd.Series(h - l, index=s.index)
    ar = rr.shift(1).rolling(12 * W, min_periods=6 * W).mean().values
    bull, bear = strong(o, h, l, c, ar, 0.6, 0.9)
    rows = []
    for q in range(15):
        M = (tod % 15) == q
        r = dict(min_of_quarter=q); r.update(stat(M & (bull | bear), np.where(bull, -1, 1)))
        rows.append(r)
    print(f'\nrolling {W}-bar window strong-close FADE, by minute-of-quarter of the signal bar (14 = bar that closes the M15)')
    print(pd.DataFrame(rows).round(3).to_string(index=False))
