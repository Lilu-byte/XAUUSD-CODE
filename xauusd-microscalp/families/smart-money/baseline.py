"""Does the SMC trigger add anything beyond its filter? For every session x HTF-trend x vol cell,
compute the TRAIN move of a dumb 'trade the trend direction at EVERY bar in the cell' baseline,
then the incremental move of each scan2 variant over it (TRAIN only)."""
import sys, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from sigs2 import *
from mlib import Harness, spread_series
H = Harness(); m1 = H.m1; c = m1.close.values
idx = m1.index; TR = idx < SPLIT
HZ = (1, 2, 3, 5, 10, 20)
F = {k: np.r_[c[k:] - c[:-k], np.full(k, np.nan)] for k in HZ}
S = sessions(m1); TRD = {'m15': trend_m15(m1), 'h1': trend_h1(m1)}; VOL = vol_regime(m1)
rows = []
for sess, tf, vf in itertools.product(S, ('m15', 'h1'), ('all', 'hi', 'lo')):
    msk = S[sess] & TR & (TRD[tf] != 0)
    if vf != 'all': msk &= VOL == (1 if vf == 'hi' else -1)
    r = dict(sess=sess, tf=tf, vol=vf)
    for k in HZ:
        r[f'with{k}'] = np.nanmean((F[k] * TRD[tf])[msk])
    rows.append(r)
B = pd.DataFrame(rows)
pd.set_option('display.width', 250)
print('Baseline: move of "trade H-trend direction at every bar" in cell (TRAIN). anti = minus this.')
print(B.round(3).to_string(index=False))

df = pd.read_csv('/mnt/project-files/xauusd-microscalp/families/smart-money/scan2_train.csv.gz')
df = df[df.n_day >= 3].copy()
for k in HZ:
    bl = np.zeros(len(df))
    for j, (t, s, v) in enumerate(zip(df.trend, df.sess, df.vol)):
        if t == 'all': continue
        w, tf = t.split('_')
        row = B[(B.sess == s) & (B.tf == tf) & (B.vol == v)].iloc[0]
        bl[j] = row[f'with{k}'] * (1 if w == 'with' else -1)
    df[f'inc{k}'] = df[f'mv{k}'] - bl
    df[f'zi{k}'] = df[f'inc{k}'] / df[f'se{k}']
    df[f'ti{k}'] = (df[f'mv{k}'] - df.spr) / df[f'se{k}']
print('\nIncremental z (move over filter baseline)/se, n_day>=3, distribution:')
print(pd.DataFrame({k: df[f'zi{k}'].describe(percentiles=[.5, .9, .99]) for k in HZ}).round(2).to_string())
for k in (1, 2, 3, 5, 10):
    d = df[(df[f'a{k}'] > df.spr) & (df[f'b{k}'] > df.spr)].sort_values(f'zi{k}', ascending=False)
    print(f'\n== h={k}: halves beat spread; top 8 by incremental z')
    print(d[['sig', 'dir', 'sess', 'trend', 'vol', 'n_day', 'spr', f'mv{k}', f'inc{k}', f'zi{k}', f'ti{k}']].head(8).round(3).to_string(index=False))
