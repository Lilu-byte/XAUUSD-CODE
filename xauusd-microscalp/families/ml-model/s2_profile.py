"""TRAIN-only diagnostic: what do the top-confidence signals of a stage-1 model look like (OOS Jul20-Aug31)?
Bar range, last-3-bar move, fade vs follow, time of day, fill-free move profile, TP=$1 bracket P&L over SL x timeout.
usage: python3 s2_profile.py 'key~q~cen' ..."""
import sys, glob
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *

H = Harness(); m1 = H.m1; T = m1.index
SLS = (0.5, 1.0, 2.0, 3.0, 5.0); TOS = (2, 5, 10, 20, 30)
A = bracket_arrays(H, brk=[(1.0, s, t) for s in SLS for t in TOS])
scores = {}
for f in sorted(glob.glob(FAM + 'tmp_s1*.npz')):
    z = np.load(f); idx = z['idx']
    for k in z.files:
        if k != 'idx': scores[k] = z[k]
rng = (m1.high - m1.low).values; c = m1.close.values
r3 = c - np.roll(c, 3); r1 = c - np.roll(c, 1)
rng_med = pd.Series(rng).rolling(60, min_periods=10).median().values
for arg in sys.argv[1:]:
    key, q, cen = arg.split('~')
    sg = signal_q(scores[key], float(q), center=bool(int(cen)))
    sel = sg != 0; ii = idx[sel]; d = sg[sel]
    print(f'\n{arg}: n={sel.sum()}  median bar range {np.median(rng[ii]):.2f} (all OOS {np.median(rng[idx]):.2f}), '
          f'range / 60-bar median: {np.median(rng[ii] / rng_med[ii]):.2f}; share with |3-bar move| > $6: {np.mean(np.abs(r3[ii]) > 6):.2f}; '
          f'fade share (dir opposite last 1-bar move): {np.mean(np.sign(r1[ii]) == -d):.2f}, opposite 3-bar move: {np.mean(np.sign(r3[ii]) == -d):.2f}')
    print('  hour-of-day counts:', pd.Series(T[ii].hour).value_counts().sort_index().to_dict())
    sig_full = np.zeros(len(m1)); sig_full[ii] = d
    print('  edge() (train row = OOS signals only, signals_day over all 47 TRAIN days):')
    print(edge(m1, sig_full, horizons=(1, 2, 3, 5, 10, 20, 30)).loc[['train']].round(3).to_string())
    tab = pd.DataFrame({to: [np.nanmean(np.where(d == 1, A[(1.0, s, to)][0][ii], A[(1.0, s, to)][1][ii])) for s in SLS] for to in TOS},
                       index=[f'SL{s}' for s in SLS])
    print('  TP $1 bracket P&L per signal, rows SL, cols timeout:'); print(tab.round(3).to_string())
