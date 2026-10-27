"""Why does per_trade exceed TP? Inspect the held-out trades (TRAIN halves only)."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from gbm_feats import *
import lightgbm as lgb
H = Harness(); m = H.m1; f = build(m); X = feature_matrix(m, f); ok = valid_mask(m, f)
idx = m.index; inA = (idx < A_SPLIT) & ok; inB = (idx >= A_SPLIT) & (idx < SPLIT) & ok
P = dict(objective='regression', learning_rate=0.03, num_leaves=15, min_data_in_leaf=400, feature_fraction=0.7,
         bagging_fraction=0.7, bagging_freq=1, lambda_l2=10, verbose=-1, num_threads=4)
tp, sl, to = 1.0, 3, 5
lab = bracket_labels(H, tp, sl, to)
pred = {}
for d in (1, -1):
    y = lab[d]; tr = inA & ~np.isnan(y)
    mdl = lgb.train(P, lgb.Dataset(X.values[tr], y[tr]), num_boost_round=200); pred[d] = mdl.predict(X.values)
    if d == 1:
        imp = pd.Series(mdl.feature_importance('gain'), index=X.columns).sort_values(ascending=False)
        print('importance (long model):', (imp / imp.sum()).round(3).head(10).to_dict())
best = np.maximum(pred[1], pred[-1]); dirn = np.where(pred[1] >= pred[-1], 1, -1)
thr = np.quantile(best[inA], .99); sig = np.where(inB & (best > thr), dirn, 0)
days, trades = H.run(sig, tp, sl, to, 1)
tt = trades[trades.entry >= A_SPLIT].copy()
print('trades', len(tt), 'pnl>tp:', (tt.pnl > tp + 1e-9).sum(), ' sum of pnl', tt.pnl.sum().round(1), ' sum of pnl beyond tp', (tt.pnl - tp).clip(lower=0).sum().round(1))
print(tt.pnl.describe().round(2).to_dict())
print('bars held of big winners', tt[tt.pnl > tp + 1e-9].bars.value_counts().to_dict())
pos = m.index.get_indexer(tt.entry)
tt['gap_next_open'] = (m.open.values[pos + 1] - m.close.values[pos]) * tt.dir.values
tt['next_min'] = (m.index[pos + 1] - m.index[pos]).total_seconds() / 60
tt['tod'] = m.tod.values[pos]; tt['spr'] = m.spread_usd.values[pos]
print('next bar minutes gap counts', tt.next_min.value_counts().head().to_dict())
print('mean gap(next open - close) in trade dir', tt.gap_next_open.mean().round(3), ' all bars mean abs gap', np.abs(m.open.values[1:] - m.close.values[:-1]).mean().round(3))
print(tt.sort_values('pnl', ascending=False).head(15).to_string())
