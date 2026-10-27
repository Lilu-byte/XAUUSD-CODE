"""FINAL (run once): refit each pick on ALL of TRAIN (< 2026-09-01), score TEST, report everything.
Picks are fixed in PICKS below, chosen from cv2/cv5/bracket results on TRAIN only."""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from feat import *
from mods import *
from mlib import *

OUT = '/mnt/project-files/xauusd-microscalp/families/ml-model/'
PICKS = json.load(open(OUT + 'picks.json'))

H = Harness(); m1 = H.m1; F = build(m1); C = cost(m1).values; T = m1.index
ok = tradeable(m1) & (np.arange(len(m1)) > 150)
TR = ok & (T < SPLIT); TE = T >= SPLIT
pd.set_option('display.width', 220)
r3 = lambda d: {k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for k, v in d.items()}
res = {}
for p in PICKS:
    name, k, fs, kind, cx, q = p['name'], p['k'], p['fs'], p['kind'], p['cx'], p['q']
    groups = {'all': list(GROUPS), 'noHTF': ['candle', 'ret', 'forming', 'ctx', 'flow'],
              'candle+forming': ['candle', 'forming']}[fs]
    cl = cols(F, groups)
    fwd = targets(m1, k).values
    tr = TR & ~np.isnan(fwd)
    m = fit(F.loc[tr, cl], fwd[tr], C[tr], kind, **(dict(num_leaves=7, n_estimators=120, min_child_samples=1000) if cx == 'small' else {}))
    s = np.full(len(m1), np.nan); s[ok] = score(m, F.loc[ok, cl])
    idx = np.where(ok)[0]
    thr = np.full(len(m1), np.nan); thr[idx] = roll_thr(s[idx], q)
    sig_all = np.zeros(len(m1), int); sig_all[idx] = signal(s[idx], thr[idx])
    sig_te = np.where(TE, sig_all, 0)
    a = dict(tp=p['tp'], sl=p['sl'], timeout=p['timeout'], max_open=p['max_open'])
    print(f'\n===== {name}: k={k} fs={fs} kind={kind} cx={cx} q={q} {a}')
    if hasattr(m, 'feature_importances_'):
        imp = pd.Series(m.booster_.feature_importance('gain'), index=cl).sort_values(ascending=False)
        print('top features (gain share):', (imp / imp.sum()).head(15).round(3).to_dict())
    d, t = H.run(sig_all, **a)
    tr_s = summarize(d, t, 'train'); print('TRAIN (in-sample refit, FAIR/base):', r3(tr_s))
    out = {'train': tr_s}
    for fill, spr in (('FAIR', 'base'), ('OHLC', 'base'), ('FAIR', 'bar'), ('FAIR', 'wide')):
        d, t = H.run(sig_te, fill=fill, spread=spr, **a)
        out[f'test_{fill}_{spr}'] = summarize(d, t, 'test')
        print(f'TEST {fill}/{spr}:', r3(out[f'test_{fill}_{spr}']))
    d, t = H.run(sig_te, **a)
    out['test_avg_spread'] = float(np.mean(H._spr['base'][t.entry.map(m1.index.get_loc).values]))
    rnd = [summarize(*H.run(random_like(sig_te, sd), **a), 'test')['per_day'] for sd in range(20)]
    out['random_per_day'] = float(np.mean(rnd)); print('TEST random-direction same bars, per_day avg 20 seeds:', round(np.mean(rnd), 3), 'sd', round(np.std(rnd), 3))
    e = edge(m1, sig_te); print('TEST edge():'); print(e.loc[['test']].round(3).to_string())
    out['test_edge_move'] = float(e.loc['test', f'move_{min([1, 2, 3, 5, 10], key=lambda h: abs(h - p["timeout"]))}m'])
    out['test_edge_move_k'] = float(e.loc['test', f'move_{k}m']) if f'move_{k}m' in e.columns else None
    # diagnostic only: accuracy / profit vs confidence on TEST
    print('TEST diagnostic by confidence quantile (not used for choosing):')
    te_idx = np.where(ok & TE)[0]
    rows = []
    for qq in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0):
        sg = np.zeros(len(m1), int)
        if qq < 1:
            th = np.full(len(m1), np.nan); th[idx] = roll_thr(s[idx], qq); sg[idx] = signal(s[idx], th[idx])
        else:
            sg[idx] = np.sign(s[idx]).astype(int)
        sg = np.where(TE, sg, 0)
        sel = (sg != 0) & ~np.isnan(fwd)
        mv = sg[sel] * fwd[sel]
        dd, tt = H.run(sg, **a); sm = summarize(dd, tt, 'test')
        rows.append(dict(q=qq, sig_day=sel.sum() / 29, hit=(mv > 0).mean(), move=mv.mean(), cost=C[sel].mean(),
                         net=mv.mean() - C[sel].mean(), per_day=sm['per_day'], trades_day=sm['trades_day'], win=sm['win']))
    diag = pd.DataFrame(rows); print(diag.round(3).to_string(index=False)); out['diag'] = diag.to_dict('records')
    res[name] = out
json.dump(res, open(OUT + 'final_test.json', 'w'), default=float, indent=1)
