"""Stage 1 (TRAIN only, mlib v2): walk-forward OOS scores inside TRAIN for many model configurations.
3 expanding folds: fit < Jul20 -> score Jul20-31; fit < Aug3 -> score Aug3-14; fit < Aug17 -> score Aug17-31.
  family A: direction at horizon k (k M1 bars) - targets bin (P(up)), reg (huber, $), zreg (huber, move/ATR14)
  family B: direct bracket target - D = (P&L long - P&L short)/2 for bracket (tp, sl, to), FAIR/base, i.e. the part of the
            bracket P&L that depends on the chosen direction (the rest, (L+S)/2, is ~ -spread for either side).
            breg = huber regression on D, bbin = classifier on D > 0 weighted by |D|.
Scores are saved to tmp_s1_<chunk>.npz (deleted at the end of the study).
usage: python3 s1_scores.py <chunk: A1|A2|B1|B2> [n_jobs]"""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *
from feat import build, targets, GROUPS, cols
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer

chunk = sys.argv[1]; NJ = int(sys.argv[2]) if len(sys.argv) > 2 else 4
STD = dict(num_leaves=15, learning_rate=0.03, n_estimators=300, min_child_samples=300, subsample=0.7, subsample_freq=1,
           colsample_bytree=0.7, reg_lambda=5.0, verbose=-1, n_jobs=NJ, random_state=1)
SMALL = {**STD, 'num_leaves': 7, 'n_estimators': 120, 'min_child_samples': 1000}
FSETS = {'all': list(GROUPS), 'noHTF': ['candle', 'ret', 'forming', 'ctx', 'flow'], 'cf': ['candle', 'forming']}


def fit_score(kind, Xtr, y, Xva, P):
    if kind == 'bin':
        m = lgb.LGBMClassifier(objective='binary', **P).fit(Xtr, (y > 0).astype(int)); return m.predict_proba(Xva)[:, 1] - .5
    if kind == 'bbin':
        m = lgb.LGBMClassifier(objective='binary', **P).fit(Xtr, (y > 0).astype(int), sample_weight=np.abs(y) + 1e-3)
        return m.predict_proba(Xva)[:, 1] - .5
    if kind in ('reg', 'zreg', 'breg'):
        q = np.nanquantile(np.abs(y), 0.99); yc = np.clip(y, -q, q)
        m = lgb.LGBMRegressor(objective='huber', alpha=float(np.nanquantile(np.abs(yc), 0.9)), **P).fit(Xtr, yc)
        return m.predict(Xva)
    if kind == 'logit':
        m = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), LogisticRegression(C=0.01, max_iter=500))
        m.fit(Xtr, (y > 0).astype(int)); return m.predict_proba(Xva)[:, 1] - .5
    raise ValueError(kind)


H = Harness(); m1 = H.m1; T = m1.index
F = build(m1)
ok = tradeable2(m1) & (np.arange(len(m1)) > 150)
fo = fold_of(T)
OOS = ok & (fo >= 1) & (fo <= 3)
idx = np.where(OOS)[0]

jobs = []   # (key, label array, kind, fs, cx)
if chunk.startswith('A'):
    ks = {'A1': (1, 2, 3), 'A2': (5, 10)}[chunk]
    a14 = F['atr14'].values.astype(float)
    for k in ks:
        fwd = targets(m1, k).values
        for kind in ('bin', 'reg', 'zreg'):
            y = fwd / a14 if kind == 'zreg' else fwd
            for fs in FSETS:
                for cx in ('std', 'small'):
                    jobs.append((f'A|{k}|{kind}|{fs}|{cx}', y, kind, fs, cx))
        jobs.append((f'A|{k}|logit|all|std', fwd, 'logit', 'all', 'std'))
else:
    brs = {'B1': [(1.0, 0.5, 5), (1.0, 1.0, 5), (1.0, 3.0, 10), (0.5, 0.5, 3)],
           'B2': [(0.5, 1.0, 5), (0.3, 0.3, 2), (0.2, 1.0, 5)]}[chunk]
    A = bracket_arrays(H, brk=brs)
    for b in brs:
        L, S = A[b]; D = ((L.astype(float) - S.astype(float)) / 2)
        for kind in ('breg', 'bbin'):
            for fs in FSETS:
                for cx in ('std', 'small'):
                    jobs.append((f'B|{b[0]}_{b[1]}_{b[2]}|{kind}|{fs}|{cx}', D, kind, fs, cx))

scores = {}; t0 = time.time()
for key, y, kind, fs, cx in jobs:
    cl = cols(F, FSETS[fs]); P = SMALL if cx == 'small' else STD
    s_all = np.full(len(m1), np.nan)
    for fi in (1, 2, 3):
        tr = ok & (T < B[fi - 1]) & ~np.isnan(y)
        va = ok & (fo == fi)
        s_all[va] = fit_score(kind, F.loc[tr, cl], y[tr], F.loc[va, cl], P)
    scores[key] = s_all[idx].astype(np.float32)
    print(f'{key:40s} {time.time() - t0:6.0f}s', flush=True)
np.savez(FAM + f'tmp_s1_{chunk}.npz', idx=idx, **scores)
print('saved', len(scores), 'configs')
