"""TRAIN-only: LightGBM on the family's features predicting the bracket P&L of a long / a short.
Fit on TRAIN-A (Jun26-Jul31), evaluate on TRAIN-B (Aug) and vice versa. Report harness per_day on the held-out half
for top-quantile thresholds."""
import sys, time; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from gbm_feats import *
import lightgbm as lgb
t0 = time.time()
H = Harness(); m = H.m1; f = build(m); X = feature_matrix(m, f); ok = valid_mask(m, f)
idx = m.index; inA = (idx < A_SPLIT) & ok; inB = (idx >= A_SPLIT) & (idx < SPLIT) & ok
P = dict(objective='regression', learning_rate=0.03, num_leaves=15, min_data_in_leaf=400, feature_fraction=0.7,
         bagging_fraction=0.7, bagging_freq=1, lambda_l2=10, verbose=-1, num_threads=4)
for tp, sl, to in ((0.3, 1, 3), (0.5, 2, 5), (1.0, 3, 5), (1.0, 8, 10)):
    lab = bracket_labels(H, tp, sl, to)
    for fit, ev, fn, en in ((inA, inB, 'A', 'B'), (inB, inA, 'B', 'A')):
        pred = {}
        for d in (1, -1):
            y = lab[d]; tr = fit & ~np.isnan(y)
            mdl = lgb.train(P, lgb.Dataset(X.values[tr], y[tr]), num_boost_round=200)
            pred[d] = mdl.predict(X.values)
        best = np.maximum(pred[1], pred[-1]); dirn = np.where(pred[1] >= pred[-1], 1, -1)
        line = [f'TP{tp} SL{sl} TO{to} fit {fn} -> eval {en}:']
        for q in (0.9, 0.97, 0.99, 0.997):
            thr = np.quantile(best[fit], q)                     # threshold from the FIT half only
            sig = np.where(ev & (best > thr), dirn, 0)
            days, trades = H.run(sig, tp, sl, to, 1)
            msk = (days.index >= (A_SPLIT if en == 'B' else idx[0].normalize())) & (days.index < (SPLIT if en == 'B' else A_SPLIT))
            dd = days[msk]; tt = trades[trades.entry.isin(idx[sig != 0])]
            line.append(f'q{q}: {dd.pnl.mean():+.2f}/d {len(tt)/len(dd):5.1f}tr/d pt {tt.pnl.mean():+.3f}')
        print('  '.join(line))
print('time', round(time.time() - t0))
