"""Stage 1: fill-free edge of every pattern / timeframe / direction / trend filter on TRAIN only.
Writes edge_train.csv (small) and prints the best rows. TEST is not touched here."""
from pats import *
H = Harness(); m = H.m1
TR = (m.index < SPLIT) & (m.tod.values < END_TOD - 15)
ndays = len(np.unique(m.index[m.index < SPLIT].date))
spr = spread_series(m, 'base')
HZ = (1, 2, 3, 5, 10)
FWD = {k: (m.close.shift(-k) - m.close).values for k in HZ}
TRD = {tf: trend(m, tf) for tf in ('M15', 'H1')}

def stats(sig):
    msk = TR & (sig != 0)
    n = msk.sum()
    r = dict(n=n, per_day=n / ndays, spread=spr[msk].mean() if n else np.nan)
    for k in HZ:
        f = FWD[k][msk] * sig[msk]; f = f[~np.isnan(f)]
        r[f'm{k}'] = f.mean() if len(f) else np.nan
        r[f't{k}'] = f.mean() / (f.std() / np.sqrt(len(f))) if len(f) > 5 else np.nan
    return r

rows = []
for tfk, mode in ((1, 'fixed'), (2, 'fixed'), (2, 'rolling'), (3, 'fixed'), (3, 'rolling')):
    S = on_m1(m, tfk, mode)
    for name, s in S.items():
        for filt in ('none', 'M15_with', 'M15_against', 'H1_with', 'H1_against'):
            if filt == 'none': base = s
            else:
                tf, w = filt.split('_'); t = TRD[tf]
                base = np.where((np.sign(s) == t) if w == 'with' else (np.sign(s) == -t), s, 0)
            for dirn, mult in (('follow', 1), ('fade', -1)):
                r = stats(np.sign(base) * mult)
                r.update(tf=f'M{tfk}', mode=mode, pattern=name, filt=filt, dir=dirn)
                rows.append(r)
df = pd.DataFrame(rows)
for k in HZ: df[f'net{k}'] = df[f'm{k}'] - df.spread
df['best_net'] = df[[f'net{k}' for k in HZ]].max(axis=1)
df.to_csv('edge_train.csv', index=False)
print('configs', len(df))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
cols = ['tf', 'mode', 'pattern', 'filt', 'dir', 'per_day', 'spread', 'm1', 'm2', 'm3', 'm5', 'm10', 't3', 't10', 'best_net']
print('\nTop 25 by best_net (TRAIN, >=1 signal/day):')
print(df[df.per_day >= 1].sort_values('best_net', ascending=False)[cols].head(25).round(3).to_string(index=False))
print('\nUnfiltered follow, M1 fixed:')
print(df[(df.tf == 'M1') & (df.filt == 'none') & (df.dir == 'follow')][cols].round(3).to_string(index=False))
print('\nShare of configs (>=1/day) with best_net>0:', (df[df.per_day >= 1].best_net > 0).mean().round(3))
