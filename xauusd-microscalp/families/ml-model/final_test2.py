"""FINAL (run once, mlib v2). The three picks below were fixed from TRAIN-only walk-forward results
(s1_scores / s4_mirror -> s2_eval -> s5_select -> s6_harness). Each pick is refitted on ALL of TRAIN (< 2026-09-01),
saved (LightGBM model text + JSON spec), scored on TEST, and reported:
  TRAIN summarize (in-sample refit; the honest TRAIN figure is the walk-forward OOS one in s6_harness.out),
  TEST FAIR/base, OHLC/base, FAIR/bar, FAIR/wide, random direction on the same bars (20 seeds), edge(),
  and a TEST confidence-threshold diagnostic (not used for any choice).
TEST signals use a trailing threshold over TEST scores only (warm-up 500 bars on Sep 1, i.e. an EA started on Sep 1)."""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *
from feat import build, targets, GROUPS, cols
from feat_mirror import mirror
import lightgbm as lgb

STD = dict(num_leaves=15, learning_rate=0.03, n_estimators=300, min_child_samples=300, subsample=0.7, subsample_freq=1,
           colsample_bytree=0.7, reg_lambda=5.0, verbose=-1, n_jobs=4, random_state=1)
FSETS = {'all': list(GROUPS), 'cf': ['candle', 'forming']}
PICKS = [
    dict(name='P1_fade_reg3_cf', k=3, kind='reg', fs='cf', mirror=False, q=0.005, center=False,
         tp=1.0, sl=5.0, timeout=30, max_open=3, cooldown=0),
    dict(name='P2_bin5_all_centered', k=5, kind='bin', fs='all', mirror=False, q=0.005, center=True,
         tp=1.0, sl=5.0, timeout=20, max_open=5, cooldown=0),
    dict(name='P3_mirror_bin5_cf', k=5, kind='bin', fs='cf', mirror=True, q=0.0025, center=False,
         tp=1.0, sl=2.0, timeout=30, max_open=2, cooldown=0),
]
DROP = ('up5', 'up10', 'rnd5', 'rnd10')
H = Harness(); m1 = H.m1; T = m1.index
F = build(m1)
ok = tradeable2(m1) & (np.arange(len(m1)) > 150)
TR = ok & (T < SPLIT); TE = ok & (T >= SPLIT)
r3 = lambda d: {k: (round(float(v), 3) if isinstance(v, (float, np.floating, int, np.integer)) else v) for k, v in d.items()}
pd.set_option('display.width', 220)
res = {}
for p in PICKS:
    name = p['name']
    cl = cols(F, FSETS[p['fs']])
    if p['mirror']: cl = [c for c in cl if c not in DROP]
    fwd = targets(m1, p['k']).values
    y = fwd
    tr = TR & ~np.isnan(y)
    X = F.loc[tr, cl]; yy = y[tr]
    if p['mirror']:
        X = pd.concat([X, mirror(X)]); yy = np.r_[yy, -yy]
    if p['kind'] == 'bin':
        m = lgb.LGBMClassifier(objective='binary', **STD).fit(X, (yy > 0).astype(int))
        f = lambda Z: m.predict_proba(Z)[:, 1] - .5
    else:
        qq = np.nanquantile(np.abs(yy), 0.99); yc = np.clip(yy, -qq, qq); alpha = float(np.nanquantile(np.abs(yc), 0.9))
        m = lgb.LGBMRegressor(objective='huber', alpha=alpha, **STD).fit(X, yc)
        f = lambda Z: m.predict(Z)
    sc = lambda Z: (f(Z) - f(mirror(Z))) / 2 if p['mirror'] else f(Z)
    m.booster_.save_model(FAM + f'model_{name}.txt')
    spec = {**p, 'features': cl, 'label': f"close[i+{p['k']}] - close[i] (bid, M1)",
            'score': ('(P(up|x) - P(up|mirror(x)))/2' if p['mirror'] and p['kind'] == 'bin' else
                      'P(up|x) - 0.5' if p['kind'] == 'bin' else 'huber regression prediction ($)'),
            'threshold': f"trade when |s| >= the {1 - p['q']:.4f} quantile of |s| over the previous 3960 scored M1 bars "
                         f"(min 500){'; s = score - trailing median of score over the previous 3960 bars' if p['center'] else ''}; "
                         'direction = sign(s)',
            'entry_window': 'M1 closes 01:05-22:29 server time, not the last bar of a session',
            'fit_rows': int(tr.sum()) * (2 if p['mirror'] else 1), 'lgb_params': STD,
            'model_file': f'model_{name}.txt', 'feature_code': 'feat.py build(m1) (+ feat_mirror.py mirror() if mirror)'}
    json.dump(spec, open(FAM + f'model_{name}.json', 'w'), indent=1, default=str)
    imp = pd.Series(m.booster_.feature_importance('gain'), index=cl).sort_values(ascending=False)
    s_tr = np.full(len(m1), np.nan); s_tr[TR] = sc(F.loc[TR, cl])
    s_te = np.full(len(m1), np.nan); s_te[TE] = sc(F.loc[TE, cl])
    sig_tr = np.zeros(len(m1), np.int64); sig_tr[TR] = signal_q(s_tr[TR], p['q'], p['center'])
    sig_te = np.zeros(len(m1), np.int64); sig_te[TE] = signal_q(s_te[TE], p['q'], p['center'])
    a = dict(tp=p['tp'], sl=p['sl'], timeout=p['timeout'], max_open=p['max_open'], cooldown=p['cooldown'])
    print(f'\n===== {name}: {p}')
    print('top features (gain share):', (imp / imp.sum()).head(12).round(3).to_dict())
    out = {}
    d, t = H.run(sig_tr, **a); out['train_insample_FAIR_base'] = summarize(d, t, 'train')
    print('TRAIN in-sample refit FAIR/base:', r3(out['train_insample_FAIR_base']))
    for fill, spr in (('FAIR', 'base'), ('OHLC', 'base'), ('FAIR', 'bar'), ('FAIR', 'wide')):
        d, t = H.run(sig_te, fill=fill, spread=spr, **a)
        out[f'test_{fill}_{spr}'] = summarize(d, t, 'test')
        print(f'TEST {fill}/{spr}:', r3(out[f'test_{fill}_{spr}']))
        if fill == 'FAIR' and spr == 'base':
            tt = t; dd = d
    ii = m1.index.get_indexer(tt.entry)
    out['test_avg_spread'] = float(H._spr['base'][ii].mean()); out['test_long_share'] = float((tt.dir == 1).mean())
    out['test_median_bars'] = float(tt.bars.median()); out['test_mean_bars'] = float(tt.bars.mean())
    print(f"TEST trades: {len(tt)}, long share {out['test_long_share']:.2f}, avg base spread {out['test_avg_spread']:.3f}, "
          f"bars held median {out['test_median_bars']:.0f} mean {out['test_mean_bars']:.1f}; P&L longs {tt.pnl[tt.dir == 1].mean():+.3f} "
          f"shorts {tt.pnl[tt.dir == -1].mean():+.3f}; trades hitting -SL: {(tt.pnl <= -p['sl'] + 1e-9).mean():.3f}")
    rnd = [summarize(*H.run(random_like(sig_te, sd), **a), 'test')['per_day'] for sd in range(20)]
    out['random_per_day'] = float(np.mean(rnd)); out['random_sd'] = float(np.std(rnd))
    print(f'TEST random direction same bars, per_day avg 20 seeds: {np.mean(rnd):+.3f} (sd {np.std(rnd):.3f})')
    e = edge(m1, sig_te, horizons=(1, 2, 3, 5, 10, 20, 30))
    print('TEST edge():'); print(e.loc[['test']].round(3).to_string())
    out['edge'] = e.loc['test'].to_dict()
    # weekly P&L
    wk = dd[dd.index >= SPLIT].pnl.resample('W').sum()
    print('TEST weekly P&L:', wk.round(2).to_dict())
    # diagnostic: confidence threshold vs profit on TEST (all signals taken; and the pick's max_open in the harness)
    Ab = bracket_arrays(H, brk=[(p['tp'], p['sl'], p['timeout'])])[(p['tp'], p['sl'], p['timeout'])]
    rows = []
    for q in (0.001, 0.0025, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0):
        sg = np.zeros(len(m1), np.int64)
        sg[TE] = signal_q(s_te[TE], q, p['center']) if q < 1 else np.sign(s_te[TE]).astype(np.int64)
        sel = sg != 0
        P = np.where(sg[sel] == 1, Ab[0][sel], Ab[1][sel]).astype(float)
        R = ((Ab[0][sel] + Ab[1][sel]) / 2).astype(float)
        dq, tq = H.run(sg, **a); sm = summarize(dq, tq, 'test')
        mv = {k: np.nanmean(sg[sel] * targets(m1, k).values[sel]) for k in (1, 3, 5)}
        rows.append(dict(q=q, sig_day=sel.sum() / 29, pnl_sig=np.nanmean(P), rand_sig=np.nanmean(R), win_sig=np.nanmean(P > 0),
                         mv1=mv[1], mv3=mv[3], mv5=mv[5], spread=H._spr['base'][sel].mean(),
                         per_day_harness=sm['per_day'], trades_day=sm['trades_day']))
    diag = pd.DataFrame(rows); out['diag'] = diag.to_dict('records')
    print('TEST diagnostic, confidence threshold vs profit (NOT used for choosing):'); print(diag.round(3).to_string(index=False))
    res[name] = out
json.dump(res, open(FAM + 'final_test2.json', 'w'), default=float, indent=1)
