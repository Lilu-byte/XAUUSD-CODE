"""Stage 5 (TRAIN only): robust cell choice for shortlisted score configs (walk-forward OOS Jul20-Aug31).
For each config x q x centring: per-fold per-day P&L (all signals taken) for every bracket with TP in 0.1-1.0; the
selection score is the fold-MIN per-day P&L averaged over the bracket's neighbours (adjacent SL and timeout values,
same TP) so that a lone lucky cell does not win. Prints the best cells per config and the direction split.
usage: python3 s5_select.py key1 key2 ..."""
import sys, glob
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *

H = Harness(); T = H.m1.index
A = bracket_arrays(H)
scores = {}
for f in sorted(glob.glob(FAM + 'tmp_s1*.npz')):
    z = np.load(f); idx = z['idx']
    for k in z.files:
        if k != 'idx': scores[k] = z[k]
fo = fold_of(T)[idx]; days = T[idx].normalize()
nd = {f: len(np.unique(days[fo == f])) for f in (1, 2, 3)}
LL = {b: A[b][0][idx] for b in BRK}; SS = {b: A[b][1][idx] for b in BRK}
rows = []
for key in sys.argv[1:]:
    for q in (0.0025, 0.005, 0.01, 0.02):
        for cen in (0, 1):
            sg = signal_q(scores[key], q, center=bool(cen)); sel = sg != 0
            if sel.sum() < 50: continue
            per = {}
            for b in BRK:
                P = np.where(sg[sel] == 1, LL[b][sel], SS[b][sel]).astype(float)
                per[b] = [np.nansum(P[fo[sel] == f]) / nd[f] for f in (1, 2, 3)]
            for b in BRK:
                tp, sl, to = b
                i_sl = SL_GRID.index(sl); i_to = TO_GRID.index(to)
                nb = [(tp, SL_GRID[a], TO_GRID[c]) for a in range(max(0, i_sl - 1), min(len(SL_GRID), i_sl + 2))
                      for c in range(max(0, i_to - 1), min(len(TO_GRID), i_to + 2))]
                fmin_nb = np.mean([min(per[x]) for x in nb])
                rows.append(dict(key=key, q=q, cen=cen, n_day=sel.sum() / 31, long=(sg[sel] == 1).mean(), tp=tp, sl=sl, to=to,
                                 pday=np.mean(per[b]), f1=per[b][0], f2=per[b][1], f3=per[b][2], fmin=min(per[b]), fmin_nb=fmin_nb))
R = pd.DataFrame(rows)
R.to_csv(FAM + 's5_cells.csv', index=False)
pd.set_option('display.width', 220)
print('cells evaluated:', len(R))
for key, g in R.groupby('key', sort=False):
    print(f'\n{key}: best 5 cells by neighbour-smoothed fold-min per-day P&L')
    print(g.sort_values('fmin_nb', ascending=False).head(5).round(3).to_string(index=False))
