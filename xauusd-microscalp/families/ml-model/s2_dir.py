"""TRAIN-only diagnostic for stage-2 candidates: split per-signal bracket P&L (OOS Jul20-Aug31) by trade direction and
compare with all-long / all-short on the same bars, to separate timing skill from the TRAIN uptrend (long bias).
usage: python3 s2_dir.py 'key~q~cen' ..."""
import sys, glob
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *

H = Harness(); T = H.m1.index
BR = [(1.0, 5.0, 30), (1.0, 3.0, 10), (1.0, 1.0, 5), (0.5, 1.0, 5), (1.0, 0.5, 5), (0.5, 0.5, 3)]
A = bracket_arrays(H, brk=BR)
scores = {}
for f in sorted(glob.glob(FAM + 'tmp_s1*.npz')):
    z = np.load(f); idx = z['idx']
    for k in z.files:
        if k != 'idx': scores[k] = z[k]
fo = fold_of(T)[idx]
for arg in sys.argv[1:]:
    key, q, cen = arg.split('~')
    sg = signal_q(scores[key], float(q), center=bool(int(cen)))
    sel = sg != 0; ii = idx[sel]; d = sg[sel]
    print(f'\n{arg}: n={sel.sum()} long share {np.mean(d == 1):.2f}')
    for b in BR:
        L, S = (x[ii].astype(float) for x in A[b])
        P = np.where(d == 1, L, S)
        print(f'  {b}: all {P.mean():+.3f} | longs {P[d == 1].mean():+.3f} (all-long same bars {L.mean():+.3f}) '
              f'| shorts {P[d == -1].mean() if (d == -1).any() else np.nan:+.3f} (all-short same bars {S.mean():+.3f}) '
              f'| long-signal bars: L-S {np.mean(L[d == 1] - S[d == 1]):+.3f}  short-signal bars: S-L '
              f'{np.mean(S[d == -1] - L[d == -1]) if (d == -1).any() else np.nan:+.3f} | by fold ' +
              ' '.join(f'{P[fo[sel] == f].mean():+.3f}' for f in (1, 2, 3)))
