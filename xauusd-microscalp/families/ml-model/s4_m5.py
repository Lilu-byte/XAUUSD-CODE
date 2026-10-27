"""Stage 4b (TRAIN only): models trained on 14+ months of M5 history (feat5.build5 features, 2025-05 onward), predicting
the next n M5 bars from each M5 close. Walk-forward with the same fold starts (Jul20 / Aug3 / Aug17); every fit uses
only M5 bars that closed (with their label window) before the fold start. Scores are placed on the M1 row whose close
is the M5 close (the feeds are identical) so stage 2 can evaluate them on the M1 bracket grid.
variant 'P' = plain fit; 'S' = mirror-augmented, antisymmetric score (see feat_mirror.py).
usage: python3 s4_m5.py <P|S> [n_jobs] -> tmp_s1F_<variant>.npz"""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *
from feat5 import build5, targets5
from feat_mirror import mirror
import lightgbm as lgb

var = sys.argv[1]; NJ = int(sys.argv[2]) if len(sys.argv) > 2 else 4
P = dict(num_leaves=15, learning_rate=0.03, n_estimators=300, min_child_samples=500, subsample=0.7, subsample_freq=1,
         colsample_bytree=0.7, reg_lambda=5.0, verbose=-1, n_jobs=NJ, random_state=1)
G5 = {'candle': lambda c: c.startswith(('c0_', 'c1_', 'c2_', 'c3_', 'c4_')),
      'ret': lambda c: c.startswith(('ret', 'vol', 'rsi', 'z', 'stoch', 'hh', 'll', 'atr')),
      'forming': lambda c: c.startswith(('f15_', 'f60_')),
      'htf': lambda c: c.startswith(('M15_', 'H1_', 'H4_')),
      'ctx': lambda c: c in ('tod', 'dow', 'd_ret', 'd_pos', 'd_rng'),
      'flow': lambda c: c.startswith('tv')}
FS = {'all': list(G5), 'noHTF': ['candle', 'ret', 'forming', 'ctx', 'flow'], 'cf': ['candle', 'forming']}

H = Harness(); m1 = H.m1; T1 = m1.index
ok1 = tradeable2(m1) & (np.arange(len(m1)) > 150); fo1 = fold_of(T1)
idx = np.where(ok1 & (fo1 >= 1) & (fo1 <= 3))[0]
d = load('M5'); d = d[d.index < SPLIT]          # nothing from TEST is loaded into the fit or the features
cache = {tf: load(tf) for tf in ('M15', 'H1', 'H4')}
F = build5(d, cache); T5 = d.index
# mirror check on build5 (reflected prices)
K = 10000.0
def flip(x):
    e = x.copy(); e['open'] = K - x.open; e['close'] = K - x.close; e['high'] = K - x.low; e['low'] = K - x.high; return e
Fm = build5(flip(d), {k: flip(v) for k, v in cache.items()}); M = mirror(F)
a = M.iloc[2000:].drop(columns=['up5']).values.astype(float); b = Fm.iloc[2000:].drop(columns=['up5']).values.astype(float)
err = np.nanmax(np.abs(a - b) / (np.abs(b) + 1e-2), axis=0)
print('mirror check, columns with rel err > 1e-3:', [c for c, e in zip(M.drop(columns=['up5']).columns, err) if e > 1e-3])
pos1 = pd.Series(np.arange(len(m1)), index=T1)
m1row = pos1.reindex(T5 + pd.Timedelta(minutes=4)).values     # M1 row whose close = this M5 close (NaN if missing)
tod5 = T5.hour * 60 + T5.minute
ok5 = (np.arange(len(d)) > 100) & ~np.isnan(m1row)
jobs = []
a14 = (d.high - d.low).rolling(14).mean().values
for n in (1, 2, 3):
    fwd = targets5(d, n).values
    for kind in ('bin', 'reg', 'zreg'):
        for fs in FS:
            jobs.append((f'F{var}|{n}|{kind}|{fs}|std', fwd / a14 if kind == 'zreg' else fwd, kind, fs))
scores = {}; t0 = time.time()
for key, y, kind, fs in jobs:
    cl = [c for c in F.columns if any(G5[g](c) for g in FS[fs]) and c != 'up5']
    s1 = np.full(len(m1), np.nan)
    for fi in (1, 2, 3):
        lo = B[fi - 1]; hi = B[fi]
        tr = (np.arange(len(d)) > 100) & (T5 < lo - pd.Timedelta(hours=1)) & ~np.isnan(y)
        va = ok5 & (T5 >= lo) & (T5 < hi)
        Xtr, ytr, Xva = F.loc[tr, cl], y[tr], F.loc[va, cl]
        if var == 'S':
            Xtr = pd.concat([Xtr, mirror(Xtr)]); ytr = np.r_[ytr, -ytr]
        if kind == 'bin':
            m = lgb.LGBMClassifier(objective='binary', **P).fit(Xtr, (ytr > 0).astype(int))
            sc = m.predict_proba(Xva)[:, 1] - .5
            if var == 'S': sc = (sc - (m.predict_proba(mirror(Xva))[:, 1] - .5)) / 2
        else:
            qq = np.nanquantile(np.abs(ytr), 0.99); yc = np.clip(ytr, -qq, qq)
            m = lgb.LGBMRegressor(objective='huber', alpha=float(np.nanquantile(np.abs(yc), 0.9)), **P).fit(Xtr, yc)
            sc = m.predict(Xva)
            if var == 'S': sc = (sc - m.predict(mirror(Xva))) / 2
        s1[m1row[va].astype(int)] = sc
    s = s1[idx]; s[~ok1[idx]] = np.nan
    scores[key] = s.astype(np.float32)
    print(f'{key:40s} scored M1 rows {np.isfinite(s).sum()} {time.time() - t0:6.0f}s', flush=True)
np.savez(FAM + f'tmp_s1F_{var}.npz', idx=idx, **scores)
print('saved', len(scores), 'configs')
