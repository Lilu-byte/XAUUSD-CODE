"""Reproduce P1 on M1 with an independent signal implementation + ea_sim._sim_next; compare with the colleague's TEST trade list."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history')
from vlib import *
m = load_m1(); A = Arr(m)
s = p1_signal(m)
d, t = run(A, s)
for nm, a, b in (('TRAIN', None, SPLIT), ('  Jun26-Jul31', None, HALF), ('  Aug', HALF, SPLIT), ('TEST', SPLIT, None)):
    print(line(f'P1 {nm}', summ(d, t, a, b)))
c = pd.read_csv('/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade/final_test_trades_P1_snap_time3.csv', parse_dates=['entry'])
te = t[t.entry >= SPLIT].reset_index(drop=True)
same = len(c) == len(te) and (c.entry.values == te.entry.values).all() and np.allclose(c.pnl.values, te.pnl.values)
print('TEST trades colleague', len(c), 'mine', len(te), 'identical:', same)
# truncation test of my signal (look-ahead)
rng = np.random.default_rng(7); idx = rng.choice(np.arange(10, len(m) - 1), 300, replace=False)
fire = np.flatnonzero(s != 0); idx = np.r_[idx, rng.choice(fire, 100, replace=False)]
bad = sum(int(p1_signal(m.iloc[:i + 1])[-1] != s[i]) for i in idx)
print('truncation test (300 random + 100 firing bars): mismatches', bad)
