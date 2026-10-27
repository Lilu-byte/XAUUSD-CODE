"""(4) look-ahead truncation test of my signal; (5b) trade-level concentration and vol-normalised view;
grid context from the colleague's grid_summary.csv (read only)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/repro/pickA')
from vA import *

d = load_m15(); s, ar = sig_A(d); S = Sim(d); days, T = S.run(s)
rng = np.random.default_rng(5)
sig_bars = np.where(s != 0)[0]
cand = np.r_[rng.integers(40, len(d) - 1, 300), rng.choice(sig_bars, 150, replace=False)]
bad = 0; bad_ar = 0
for i in cand:
    dc = d.iloc[:i + 1]
    sc, arc = sig_A(dc)
    bad += int(sc[i] != s[i]); bad_ar += int(not (np.isnan(arc[i]) and np.isnan(ar[i])) and abs(arc[i] - ar[i]) > 1e-9)
print(f'(4) truncation test: {len(cand)} cut points (300 random bars + 150 signal bars): signal mismatches {bad}, AR mismatches {bad_ar}')
# also: the entry filter uses bar i+1 (gap and spread) -- that is information available at bar i+1's first tick, i.e. at entry time.

# (5b) trade concentration
for nm, (lo, hi) in (('TRAIN', TRAIN), ('TEST', TEST)):
    t = T[(T.entry >= pd.Timestamp(lo)) & (T.entry < pd.Timestamp(hi))].copy()
    nd = per(days, T, lo, hi)['days']
    srt = t.pnl.sort_values(ascending=False)
    tot = t.pnl.sum()
    print(f"(5b) {nm}: total {tot:+.1f}; best trade {srt.iloc[0]:+.1f} ({srt.iloc[0] / tot:.2f} of total); "
          + '; '.join(f"without best {k} trades {srt.iloc[k:].sum() / nd:+.3f}/d" for k in (1, 3, 5, 10)))
    t['ar'] = ar[t.ei.values]; x = t.pnl / t.ar
    print(f"      $/trade in units of AR32: mean {x.mean():+.3f}, t {x.mean() / (x.std(ddof=1) / np.sqrt(len(x))):+.2f}; long {x[t.dir == 1].mean():+.3f} (n {int((t.dir == 1).sum())}) short {x[t.dir == -1].mean():+.3f}; "
          f"median AR {t.ar.median():.2f}; stop $25 = {np.median(25 / t.ar):.2f} AR (median)")
    # vol-normalised sizing: risk 1 AR-unit per trade (size = median AR / AR)
    w = t.ar.median() / t.ar
    print(f"      vol-normalised sizing (size = median AR / AR): {(t.pnl * w).sum() / nd:+.3f}/d")
# the whole fade family in the colleague's grid (M15, 144 settings): how special is the pick?
G = pd.read_csv('/mnt/project-files/xauusd-microscalp/families/snapback-history/grid_summary.csv')
g = G[G.tf == 'M15']
K = ['n', 'k', 'gate', 'N', 'sl', 'max_open']
W = g.pivot_table(index=K, columns='period', values=['per_day', 'rand_beats', 'long_per_day', 'rand_per_day'])
pk = (2, 4.0, 1, 4, 25, 3)
for p in ('SEL', 'LATER', 'LATER_CLEAN', 'M1ERA'):
    col = W[('per_day', p)]
    print(f"grid M15 {p}: pick {col.loc[pk]:+.3f} rank {int((col > col.loc[pk]).sum()) + 1}/{len(col)}; median {col.median():+.3f}; "
          f"share of settings beating all 20 random seeds {(W[('rand_beats', p)] == 0).mean():.2f}; share above own always-long {(col > W[('long_per_day', p)]).mean():.2f}")
# SEL-rank vs LATER correlation across settings (does in-sample rank predict out-of-sample?)
from scipy.stats import spearmanr
print('Spearman SEL vs LATER $/day across 144 M15 settings: %.2f' % spearmanr(W[('per_day', 'SEL')], W[('per_day', 'LATER')]).correlation)
print('Spearman SEL vs LATER (per_day minus always-long) : %.2f' % spearmanr(W[('per_day', 'SEL')] - W[('long_per_day', 'SEL')],
                                                                   W[('per_day', 'LATER')] - W[('long_per_day', 'LATER')]).correlation)
print('total colleague grid settings', G.groupby(['tf'] + K).ngroups)
