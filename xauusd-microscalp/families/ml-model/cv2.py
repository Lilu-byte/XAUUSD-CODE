"""Stage 2 (TRAIN only): 3-fold expanding walk-forward inside TRAIN.
  fold1 fit Jun26-Jul17 -> val Jul20-Jul31; fold2 fit ..Jul31 -> val Aug3-14; fold3 fit ..Aug14 -> val Aug17-31.
OOS scores on Jul20-Aug31 (31 days). Signal rule = live-implementable trailing quantile of |score|
(previous 3 days of scores). Metric: avg favourable bid move at horizon vs avg cost, per fold and pooled.
usage: python3 cv2.py k"""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from feat import *
from mods import *
from mlib import load_m1, END_TOD

k = int(sys.argv[1])
OUT = '/mnt/project-files/xauusd-microscalp/families/ml-model/'
m1 = load_m1(); F = build(m1); C = cost(m1).values
ok = tradeable(m1) & (np.arange(len(m1)) > 150)
T = m1.index
B = [pd.Timestamp(x) for x in ('2026-07-20', '2026-08-03', '2026-08-17', '2026-09-01')]
OOS = ok & (T >= B[0]) & (T < B[3])
fold = np.searchsorted(np.array(B[1:]), T.values, side='right') + 1   # 1,2,3 within OOS
FSETS = {'all': list(GROUPS), 'noHTF': ['candle', 'ret', 'forming', 'ctx', 'flow'],
         'candle+forming': ['candle', 'forming']}
VARIANTS = [(kind, 'std') for kind in ('bin', 'binw', 'tri', 'reg', 'logit')] + \
           [(kind, 'small') for kind in ('bin', 'binw', 'tri', 'reg')]
SMALL = dict(num_leaves=7, n_estimators=120, min_child_samples=1000)
QS = (0.005, 0.01, 0.02, 0.05, 0.1, 0.2)
fwd = targets(m1, k).values
rows = []; scores = {}; t0 = time.time()
for fs, groups in FSETS.items():
    cl = cols(F, groups)
    for kind, cx in VARIANTS:
        s_all = np.full(len(m1), np.nan)
        for fi in range(3):
            tr = ok & (T < B[fi]) & ~np.isnan(fwd)
            va = ok & (T >= B[fi]) & (T < B[fi + 1])
            m = fit(F.loc[tr, cl], fwd[tr], C[tr], kind, **(SMALL if cx == 'small' else {}))
            s_all[va] = score(m, F.loc[va, cl])
        idx = np.where(OOS)[0]; s = s_all[idx]
        scores[f'{k}|{fs}|{kind}|{cx}'] = s.astype(np.float32)
        f = fwd[idx]; c = C[idx]; fo = fold[idx]; dd = T[idx].normalize()
        for q in QS:
            sig = signal(s, roll_thr(s, q))
            sel = (sig != 0) & ~np.isnan(f)
            g = sig[sel] * f[sel] - c[sel]
            r = dict(k=k, fs=fs, kind=kind, cx=cx, q=q, n_day=sel.sum() / 31, move=(sig[sel] * f[sel]).mean(),
                     cost=c[sel].mean(), net=g.mean(), hit=(sig[sel] * f[sel] > 0).mean(), long=(sig[sel] > 0).mean())
            for fi in (1, 2, 3):
                r[f'net_f{fi}'] = g[fo[sel] == fi].mean()
            dn = pd.Series(g).groupby(dd[sel]).sum()
            r['pos_days'] = (dn > 0).mean()
            rows.append(r)
        print(f'k={k} {fs} {kind} {cx} {time.time() - t0:.0f}s', flush=True)
R = pd.DataFrame(rows)
R.to_csv(OUT + f'cv2_k{k}.csv', index=False)
np.savez_compressed(OUT + f'tmp_scores_k{k}.npz', idx=np.where(OOS)[0], **scores)
pd.set_option('display.width', 220)
print(R.pivot_table(index=['fs', 'kind', 'cx'], columns='q', values='net').round(3))
print(R[R.q <= 0.1].sort_values('net', ascending=False).head(12).round(3).to_string(index=False))
