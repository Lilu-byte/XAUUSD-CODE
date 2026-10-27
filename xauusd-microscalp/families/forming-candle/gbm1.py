"""TRAIN-only 2-fold check of a LightGBM model on forming-candle features.
Fold A: fit July -> score August (forward). Fold B: fit August -> score July (backward).
Target: clip(next-k-minute bid move, -cap, cap). Trade the top-q |prediction| bars in the predicted
direction; bracket through the harness (FAIR/base) on the scored half only."""
import sys, itertools, time, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from gbm_feats import *
import lightgbm as lgb

H = Harness(); m1 = H.m1; X = build(m1); Z = gbm_matrix(m1, X); F = fwd(m1)
H1 = pd.Timestamp('2026-08-01')
idx = m1.index
A = (idx < H1); B = (idx >= H1) & (idx < SPLIT)
PAR = dict(objective='regression', learning_rate=0.03, num_leaves=15, min_data_in_leaf=300, feature_fraction=0.7,
           bagging_fraction=0.7, bagging_freq=1, lambda_l2=10, verbose=-1, num_threads=4)
ROUNDS = 300
GRID = list(itertools.product((0.3, 0.5, 1.0), (1.0, 3.0), (2, 5, 10), (1, 3)))
rows = []
t0 = time.time()
for k, cap in ((1, 1.5), (2, 1.5), (3, 1.5), (2, 3.0)):
    y = np.clip(F[k], -cap, cap)
    preds = np.full(len(m1), np.nan)
    for fit, score in ((A, B), (B, A)):
        ok = fit & np.isfinite(y)
        mdl = lgb.train(PAR, lgb.Dataset(Z.values[ok], y[ok]), ROUNDS)
        preds[score] = mdl.predict(Z.values[score])
    for fold, score in (('A_fwd', B), ('B_bwd', A)):
        p = preds[score]
        yy = y[score]; okk = np.isfinite(yy)
        ic = np.corrcoef(p[okk], yy[okk])[0, 1]
        for q in (0.01, 0.03, 0.1, 0.25):
            th = np.quantile(np.abs(p), 1 - q)
            s = np.zeros(len(m1)); s[score] = np.where(p > th, 1, np.where(p < -th, -1, 0))
            mv = np.nanmean((F[k] * s)[s != 0]); cp = np.nanmean((np.clip(F[k], -1.2, 1.2) * s)[s != 0])
            spr = X.spr.values[s != 0].mean()
            for tp, sl, to, mo in GRID:
                days, trades = H.run(s, tp, sl, timeout=to, max_open=mo)
                dsel = days[(days.index >= (H1 if fold == 'A_fwd' else idx[0].normalize())) & (days.index < (SPLIT if fold == 'A_fwd' else H1))]
                tsel = trades[trades.entry.isin(idx[score])]
                rows.append(dict(k=k, cap=cap, fold=fold, ic=ic, q=q, mv=mv, cap_mv=cp, spr=spr, tp=tp, sl=sl, to=to, mo=mo,
                                 per_day=dsel.pnl.mean(), trades_day=len(tsel) / len(dsel), per_trade=tsel.pnl.mean(),
                                 win=(tsel.pnl > 0).mean()))
    print(f'k={k} cap={cap} done {time.time() - t0:.0f}s', flush=True)
R = pd.DataFrame(rows)
R.to_csv(FC + 'gbm1_train.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
print('\nOOF information: IC and move in signal direction vs spread (per fold, per q):')
print(R.groupby(['k', 'cap', 'fold', 'q'])[['ic', 'mv', 'cap_mv', 'spr', 'trades_day']].first().round(3).to_string())
W = R.pivot_table(index=['k', 'cap', 'q', 'tp', 'sl', 'to', 'mo'], columns='fold', values=['per_day', 'per_trade'])
W.columns = [f'{a}_{b}' for a, b in W.columns]
W['min_pd'] = W[['per_day_A_fwd', 'per_day_B_bwd']].min(axis=1)
print('\nTop 25 configs by min(per_day) over the two folds:')
print(W.sort_values('min_pd', ascending=False).head(25).round(3).to_string())
print('\nShare of configs with per_trade > 0 in both folds:', ((W.per_trade_A_fwd > 0) & (W.per_trade_B_bwd > 0)).mean().round(3))
