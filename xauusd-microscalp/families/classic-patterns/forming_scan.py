"""TRAIN only (halves A/B): patterns on the FORMING M5 candle (known at each M1 close, minute 2-4 of 5):
strong body (marubozu-like) and hammer / shooting-star shapes, optionally vs the H1/M15 trend,
followed or faded. 'Before the candle ends' version of the family."""
from sigs import *
H = Harness(); m = H.m1
ok = m.tod.values < END_TOD - 15
A = ok & (m.index < pd.Timestamp('2026-08-01')); B = ok & (m.index >= pd.Timestamp('2026-08-01')) & (m.index < SPLIT)
nA = len(np.unique(m.index[A].date)); nB = len(np.unique(m.index[B].date))
spr = spread_series(m, 'base'); HZ = (1, 2, 3, 5, 10)
FWD = {k: (m.close.shift(-k) - m.close).values for k in HZ}
f = forming(m, 5)
# average body of the previous 20 CLOSED M5 candles (built from M1), known at each row
c5 = resample(m, 5); ab = (c5.close - c5.open).abs().rolling(20).mean()
avg5 = htf_on_m1(m, c5, 'M5', ab.values).values
o, h, l, c = f.f_open.values, f.f_high.values, f.f_low.values, f.f_close.values
body = np.abs(c - o); rng = h - l; up = h - np.maximum(o, c); lo = np.minimum(o, c) - l
col = np.sign(c - o); fm = f.f_minute.values
prev_down = (m.close.shift(1) < m.close.shift(6)).values; prev_up = (m.close.shift(1) > m.close.shift(6)).values
T = {'none': np.ones(len(m)), 'M15': trend(m, 'M15'), 'H1': trend(m, 'H1')}
rows = []
def rec(sg, **kw):
    r = dict(kw)
    for lab, msk, nd in (('A', A, nA), ('B', B, nB)):
        g = msk & (sg != 0); r['day' + lab] = g.sum() / nd
        for hh in HZ: r[f'{lab}{hh}'] = np.nanmean(FWD[hh][g] * sg[g] - spr[g]) if g.sum() > 10 else np.nan
    rows.append(r)
for mnt in (2, 3, 4):
    at = fm == mnt
    for q in (1.0, 2.0):
        for fr in (0.75, 0.9):
            s = np.where(at & (body >= q * avg5) & (body >= fr * rng), col, 0)
            for htf in ('none', 'M15', 'H1'):
                for rel in (('all',) if htf == 'none' else ('against', 'with')):
                    s2 = s if rel == 'all' else np.where(s == (-T[htf] if rel == 'against' else T[htf]), s, 0)
                    for dirn, mu in (('follow', 1), ('fade', -1)):
                        rec(s2 * mu, kind='strong', minute=mnt, q=q, fr=fr, htf=htf, rel=rel, dir=dirn)
    ham = at & (lo >= 2 * body) & (up <= 0.5 * body + 0.05 * rng) & (body <= 0.35 * rng) & (rng >= avg5)
    inv = at & (up >= 2 * body) & (lo <= 0.5 * body + 0.05 * rng) & (body <= 0.35 * rng) & (rng >= avg5)
    s = np.where(ham & prev_down, 1, 0) + np.where(inv & prev_up, -1, 0)   # hammer bullish, shooting star bearish
    for dirn, mu in (('follow', 1), ('fade', -1)):
        rec(s * mu, kind='hammer/star', minute=mnt, q=np.nan, fr=np.nan, htf='none', rel='all', dir=dirn)
df = pd.DataFrame(rows)
mn = np.minimum(df[[f'A{k}' for k in HZ]].values, df[[f'B{k}' for k in HZ]].values)
df['rob'] = np.nanmax(mn, 1)
df.to_csv('forming_train.csv', index=False)
pd.set_option('display.width', 250)
print('configs', len(df))
c_ = ['kind','minute','q','fr','htf','rel','dir','dayA','dayB','A1','B1','A2','B2','A3','B3','A5','B5','rob']
print(df[(df.dayA >= 2) & (df.dayB >= 2)].sort_values('rob', ascending=False)[c_].head(15).round(3).to_string(index=False))
print(df[df.kind == 'hammer/star'][c_].round(3).to_string(index=False))
