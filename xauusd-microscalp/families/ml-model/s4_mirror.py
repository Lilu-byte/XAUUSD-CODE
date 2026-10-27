"""Stage 4a (TRAIN only): direction-symmetric models. Same walk-forward folds as stage 1, but each training set is
augmented with its mirror image (feat_mirror.mirror, label sign flipped) and the score is made exactly antisymmetric:
s(x) = (f(x) - f(mirror(x))) / 2. Columns up5/up10/rnd5/rnd10 are dropped (not exactly mirrorable).
usage: python3 s4_mirror.py <chunk: MA|MB> [n_jobs]   -> tmp_s1M_<chunk>.npz"""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *
from feat import build, targets, GROUPS, cols
from feat_mirror import mirror
import lightgbm as lgb

chunk = sys.argv[1]; NJ = int(sys.argv[2]) if len(sys.argv) > 2 else 4
STD = dict(num_leaves=15, learning_rate=0.03, n_estimators=300, min_child_samples=300, subsample=0.7, subsample_freq=1,
           colsample_bytree=0.7, reg_lambda=5.0, verbose=-1, n_jobs=NJ, random_state=1)
FSETS = {'all': list(GROUPS), 'noHTF': ['candle', 'ret', 'forming', 'ctx', 'flow'], 'cf': ['candle', 'forming']}
DROP = ('up5', 'up10', 'rnd5', 'rnd10')


def fit_sym(kind, Xtr, y, Xva, P):
    Xa = pd.concat([Xtr, mirror(Xtr)]); ya = np.r_[y, -y]
    Xm = mirror(Xva)
    if kind == 'bin':
        m = lgb.LGBMClassifier(objective='binary', **P).fit(Xa, (ya > 0).astype(int))
        return (m.predict_proba(Xva)[:, 1] - m.predict_proba(Xm)[:, 1]) / 2
    q = np.nanquantile(np.abs(ya), 0.99); yc = np.clip(ya, -q, q)
    m = lgb.LGBMRegressor(objective='huber', alpha=float(np.nanquantile(np.abs(yc), 0.9)), **P).fit(Xa, yc)
    return (m.predict(Xva) - m.predict(Xm)) / 2


H = Harness(); m1 = H.m1; T = m1.index
F = build(m1)
ok = tradeable2(m1) & (np.arange(len(m1)) > 150)
fo = fold_of(T)
idx = np.where(ok & (fo >= 1) & (fo <= 3))[0]
a14 = F['atr14'].values.astype(float)
jobs = []
if chunk == 'MA':
    for k in (1, 2, 3, 5, 10):
        fwd = targets(m1, k).values
        for kind in ('bin', 'reg', 'zreg'):
            for fs in ('cf', 'all'):
                jobs.append((f'M|{k}|{kind}|{fs}|std', fwd / a14 if kind == 'zreg' else fwd, 'bin' if kind == 'bin' else 'reg', fs))
else:
    for k in (2, 3, 5):
        fwd = targets(m1, k).values
        for kind in ('bin', 'reg', 'zreg'):
            jobs.append((f'M|{k}|{kind}|noHTF|std', fwd / a14 if kind == 'zreg' else fwd, 'bin' if kind == 'bin' else 'reg', 'noHTF'))
    brs = [(1.0, 3.0, 10), (1.0, 5.0, 20), (1.0, 1.0, 5), (0.5, 1.0, 5)]
    A = bracket_arrays(H, brk=brs)
    for b in brs:
        L, S = A[b]; D = (L.astype(float) - S.astype(float)) / 2
        for fs in ('cf', 'all'):
            jobs.append((f'MB|{b[0]}_{b[1]}_{b[2]}|breg|{fs}|std', D, 'reg', fs))
scores = {}; t0 = time.time()
for key, y, kind, fs in jobs:
    cl = [c for c in cols(F, FSETS[fs]) if c not in DROP]
    s_all = np.full(len(m1), np.nan)
    for fi in (1, 2, 3):
        tr = ok & (T < B[fi - 1]) & ~np.isnan(y)
        va = ok & (fo == fi)
        s_all[va] = fit_sym(kind, F.loc[tr, cl], y[tr], F.loc[va, cl], STD)
    scores[key] = s_all[idx].astype(np.float32)
    print(f'{key:40s} {time.time() - t0:6.0f}s', flush=True)
np.savez(FAM + f'tmp_s1M_{chunk}.npz', idx=idx, **scores)
print('saved', len(scores), 'configs')
