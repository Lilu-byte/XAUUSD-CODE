"""TRAIN only. Anatomy of the end-of-quarter-hour fade on the forming M15 candle:
by which quarter of the hour, by hour of day, by threshold, robust stats (median, hit rate, trimmed)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from feats import *

m1 = load_m1(); X = build(m1); F = fwd(m1)
TR = X.train.values; ND = len(np.unique(m1.index[TR].date))
tod = m1.tod.values; moh = tod % 60; hour = tod // 60
o, h, l, cc, mm = (X['f15' + k].values for k in 'ohlcm'); ar = X['f15ar12'].values
rg = h - l; bn = (cc - o) / ar; clv = np.where(rg > 0, (cc - l) / np.where(rg > 0, rg, 1), .5)
pd.set_option('display.width', 250)


def st(msk, d):
    msk = msk & TR
    if msk.sum() < 5: return dict(n_day=msk.sum() / ND)
    r = dict(n_day=msk.sum() / ND, spr=X.spr.values[msk].mean())
    for k in (1, 2, 3, 5):
        v = F[k][msk] * d[msk]
        r[f'mv{k}'] = np.nanmean(v)
    v = F[2][msk] * d[msk]; v = v[np.isfinite(v)]
    r['med2'] = np.median(v); r['hit2'] = (v > 0).mean()
    lo, hi = np.percentile(v, [5, 95]); r['trim2'] = v[(v >= lo) & (v <= hi)].mean()
    return r


def sig(thr, cl, mins):
    bull = (bn > thr) & (clv >= cl); bear = (bn < -thr) & (clv <= 1 - cl)
    M = np.isin(mm, mins)
    return M & (bull | bear), np.where(bull, -1, 1)


print('Threshold grid, minutes 14-15 of the forming M15 (FADE):')
rows = []
for thr in (0.2, 0.4, 0.6, 0.8, 1.0, 1.5):
    for cl in (0.6, 0.75, 0.9, 1.0):
        s, d = sig(thr, cl, (14, 15))
        r = dict(thr=thr, clv=cl); r.update(st(s, d)); rows.append(r)
print(pd.DataFrame(rows).round(3).to_string(index=False))

s, d = sig(0.6, 0.9, (14, 15))
print('\nBy quarter of the hour (thr .6 clv .9, min 14-15):')
rows = []
for q in range(4):
    Q = (moh // 15) == q
    r = dict(quarter=q * 15); r.update(st(s & Q, d)); rows.append(r)
print(pd.DataFrame(rows).round(3).to_string(index=False))
print('\nBy hour of day (server) (thr .6 clv .9, min 14-15):')
rows = []
for hh in range(1, 24):
    r = dict(hour=hh); r.update(st(s & (hour == hh), d)); rows.append(r)
print(pd.DataFrame(rows).round(3).to_string(index=False))
print('\nBy week of TRAIN:')
wk = m1.index.isocalendar().week.values
rows = []
for w in np.unique(wk[TR]):
    r = dict(week=w); r.update(st(s & (wk == w), d)); rows.append(r)
print(pd.DataFrame(rows).round(3).to_string(index=False))
