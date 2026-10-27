"""Reproduce P2 on M1 from the rule text (p2v) + ea_sim._sim_next; compare with the family's TEST trade list; truncation test."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *
m = load_tf('M1'); A = Arr(m)
s = A.signal()
d, t = A.run(s)
for nm, a, b in (('TRAIN', None, SPLIT), ('  Jun26-Jul31', None, HALF), ('  Aug', HALF, SPLIT), ('TEST', SPLIT, None)):
    print(line(f'P2 {nm}', summ(d, t, a, b)))
c = pd.read_csv(FAM + 'final_test_trades_P2_vwap_pullback_time15.csv', parse_dates=['entry'])
te = t[t.entry >= SPLIT].reset_index(drop=True)
same = len(c) == len(te) and (c.entry.values == te.entry.values).all() and np.allclose(c.pnl.values, te.pnl.values)
print('TEST trades family', len(c), 'mine', len(te), 'identical:', same)
# average cost actually paid per trade (base model): long pays entry-bar spread, short pays exit-bar spread
sp = A.spread('base'); ei = t.ei.values + 1; xi = t.xi.values
paid = np.where(t.dir.values == 1, sp[ei], sp[xi])
print(f'avg base spread paid per trade: TRAIN {paid[t.entry < SPLIT].mean():.3f}  TEST {paid[t.entry >= SPLIT].mean():.3f}')
# truncation test: recompute the signal on data cut right after bar i
rng = np.random.default_rng(11); idx = rng.choice(np.arange(300, len(m) - 1), 300, replace=False)
fire = np.flatnonzero(s != 0); idx = np.r_[idx, rng.choice(fire, 100, replace=False)]
bad = 0
for i in idx:
    Ai = Arr(m.iloc[:i + 1]); bad += int(Ai.signal()[-1] != s[i])
print('truncation test (300 random + 100 firing bars): mismatches', bad)
print('session tod range M1:', m.tod.min(), m.tod.max())
