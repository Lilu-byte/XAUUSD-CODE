"""Stage 1 (TRAIN only): fit Jun26-Jul31, validate Aug. Grid: horizon x target kind x feature set.
Metric (fill-free): on the top-q most confident Aug bars, avg favourable bid move at the horizon vs avg cost."""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from feat import *
from mods import *
from mlib import load_m1, END_TOD
from scipy.stats import spearmanr

m1 = load_m1(); F = build(m1); C = cost(m1).values
ok = tradeable(m1) & (np.arange(len(m1)) > 150)
FIT = ok & (m1.index < pd.Timestamp('2026-08-01'))
VAL = ok & (m1.index >= pd.Timestamp('2026-08-01')) & (m1.index < pd.Timestamp('2026-09-01'))
nval_days = len(np.unique(m1.index[VAL].date))
FSETS = {'all': list(GROUPS), 'noHTF': ['candle', 'ret', 'forming', 'ctx', 'flow'],
         'candle+forming': ['candle', 'forming']}
QS = (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 1.0)
rows = []; t0 = time.time()
for k in (2, 3, 5):
    fwd = targets(m1, k).values
    tr = FIT & ~np.isnan(fwd); va = VAL & ~np.isnan(fwd)
    for fs, groups in FSETS.items():
        cl = cols(F, groups); Xtr = F.loc[tr, cl]; Xva = F.loc[va, cl]
        for kind in ('bin', 'binw', 'tri', 'reg', 'logit'):
            m = fit(Xtr, fwd[tr], C[tr], kind)
            s = score(m, Xva); f = fwd[va]; c = C[va]
            rho = spearmanr(s, f).correlation
            for q in QS:
                thr = np.quantile(np.abs(s), 1 - q); sel = np.abs(s) >= thr
                mv = (np.sign(s[sel]) * f[sel]).mean()
                rows.append(dict(k=k, fs=fs, kind=kind, q=q, n_day=sel.sum() / nval_days, rho=rho,
                                 hit=(np.sign(s[sel]) * f[sel] > 0).mean(), move=mv, cost=c[sel].mean(),
                                 net=mv - c[sel].mean(), long=(s[sel] > 0).mean()))
        print(f'k={k} {fs} done {time.time() - t0:.0f}s', flush=True)
R = pd.DataFrame(rows)
R.to_csv('/mnt/project-files/xauusd-microscalp/families/ml-model/cv1_val.csv', index=False)
pd.set_option('display.width', 200)
print('configs:', len(R))
print('\nrank corr(score, fwd) on Aug by model:')
print(R[R.q == 1.0].pivot_table(index=['fs', 'kind'], columns='k', values='rho').round(4))
print('\nnet ($/signal, move - cost) on Aug by q:')
print(R.pivot_table(index=['k', 'fs', 'kind'], columns='q', values='net').round(3))
print('\ntop 15 by net (q<=0.2):')
print(R[R.q <= 0.2].sort_values('net', ascending=False).head(15).round(3).to_string(index=False))
