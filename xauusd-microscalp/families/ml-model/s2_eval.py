"""Stage 2 (TRAIN only): turn the stage-1 walk-forward OOS scores (Jul20-Aug31, 31 days) into live signals
(trailing top-q |score|, optionally re-centred by the trailing median) and evaluate every signal set on the full
216-bracket grid (TP 0.1-1.0 x SL 0.3-5 x timeout 2-30, FAIR fill, base spread), all signals taken (max_open = inf).
Per signal: P&L, P&L of the opposite direction, random-direction baseline (L+S)/2 on the same bars, fill-free moves.
Also 30 pure-noise score sets through the same pipeline, to show how high the best grid cell gets by luck.
usage: python3 s2_eval.py [score-file glob] [output tag]
Writes s2_summary<tag>.csv (one row per config x q x centring) and tmp_s2_grid.npz (per-bracket, per-fold P&L)."""
import sys, glob, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *
from feat import targets

QS = (0.0025, 0.005, 0.01, 0.02, 0.05, 0.1)
H = Harness(); m1 = H.m1; T = m1.index
A = bracket_arrays(H)
keys_b = list(A.keys())
spr = H._spr['base']
mv = {k: targets(m1, k).values for k in (1, 2, 3, 5, 10)}

PAT = sys.argv[1] if len(sys.argv) > 1 else 'tmp_s1_[AB]*.npz'
TAG = sys.argv[2] if len(sys.argv) > 2 else ''
NOISE = 30 if TAG == '' else 0
scores = {}; idx = None
for f in sorted(glob.glob(FAM + PAT)):
    z = np.load(f)
    if idx is None: idx = z['idx']
    assert (z['idx'] == idx).all()
    for k in z.files:
        if k != 'idx': scores[k] = z[k]
rng = np.random.default_rng(123)
for j in range(NOISE):
    scores[f'N|noise{j}|-|-|-'] = rng.standard_normal(len(idx)).astype(np.float32)
print('configs', len(scores), 'OOS rows', len(idx))

LL = np.stack([A[b][0][idx] for b in keys_b]).astype(np.float32)   # (216, n)
SS = np.stack([A[b][1][idx] for b in keys_b]).astype(np.float32)
fo = fold_of(T)[idx]; days = T[idx].normalize(); nday = len(np.unique(days)); nday_f = {f: len(np.unique(days[fo == f])) for f in (1, 2, 3)}
sp = spr[idx]
MV = {k: v[idx] for k, v in mv.items()}

rows = []; grid = {}; t0 = time.time()
for key, s in scores.items():
    for q in QS:
        for cen in (0, 1):
            sg = signal_q(s, q, center=bool(cen))
            sel = np.where(sg != 0)[0]
            if len(sel) < 50: continue
            d = sg[sel]
            P = np.where(d == 1, LL[:, sel], SS[:, sel])           # (216, nsig)
            R = (LL[:, sel] + SS[:, sel]) / 2                        # random-direction baseline per bar
            out = np.zeros((len(keys_b), 4), np.float32)
            out[:, 0] = np.nanmean(P, axis=1)
            for f in (1, 2, 3):
                m = fo[sel] == f
                out[:, f] = np.nanmean(P[:, m], axis=1) if m.sum() else np.nan
            grid[(key, q, cen)] = out
            exc = np.nanmean(P - R, axis=1)
            sd = np.nanstd(P - R, axis=1) / np.sqrt(len(sel))
            b = int(np.nanargmax(out[:, 0]))
            r = dict(key=key, q=q, cen=cen, n_day=len(sel) / nday, long=(d == 1).mean(), spread=sp[sel].mean())
            for k, v in MV.items():
                r[f'mv{k}'] = np.nanmean(d * v[sel])
            r.update(best_tp=keys_b[b][0], best_sl=keys_b[b][1], best_to=keys_b[b][2], best=out[b, 0],
                     best_f1=out[b, 1], best_f2=out[b, 2], best_f3=out[b, 3], best_exc=exc[b], best_z=exc[b] / sd[b],
                     best_rnd=np.nanmean(R[b]), grid_med=np.nanmedian(out[:, 0]), grid_pos=(out[:, 0] > 0).mean(),
                     grid_pos3=((out[:, 1:] > 0).all(axis=1)).mean(), exc_med=np.nanmedian(exc), z_med=np.nanmedian(exc / sd))
            rows.append(r)
    print(f'{key:40s} {time.time() - t0:5.0f}s', flush=True)
R = pd.DataFrame(rows)
R.to_csv(FAM + f's2_summary{TAG}.csv', index=False)
gk = list(grid.keys())
np.savez_compressed(FAM + f'tmp_s2_grid{TAG}.npz', grid=np.stack([grid[k] for k in gk]),
                    keys=np.array(['%s~%s~%d' % k for k in gk]), brk=np.array(keys_b))
print('rows', len(R), ' bracket-level evaluations', len(R) * len(keys_b))
