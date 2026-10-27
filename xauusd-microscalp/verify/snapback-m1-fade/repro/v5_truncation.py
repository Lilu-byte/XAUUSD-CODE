"""(4) Look-ahead truncation test. Signal of bar i recomputed on data cut right after bar i (must equal the full-data
value); the entry filter (gap to bar i+1, spread of bar i+1 -- known at the entry tick) recomputed on data cut right
after bar i+1. 400 random bars + 200 bars where the full-data signal fires."""
from common import *

m = load_m1()
full_raw = raw_signal(m.close.values)
full_f = entry_filter(m, full_raw)
rng = np.random.default_rng(11)
idx = np.r_[rng.choice(np.arange(10, len(m) - 2), 400, replace=False),
            rng.choice(np.flatnonzero(full_raw != 0), 200, replace=False)]
bad_raw = bad_f = 0; nz = 0
for i in idx:
    mt = m.iloc[:i + 1]
    r = raw_signal(mt.close.values)
    bad_raw += int(r[-1] != full_raw[i]); nz += int(full_raw[i] != 0)
    mt2 = m.iloc[:i + 2]
    f2 = entry_filter(mt2, raw_signal(mt2.close.values))
    bad_f += int(f2[-2] != full_f[i])
print(f'truncation test on {len(idx)} bars ({nz} with a non-zero signal): signal mismatches {bad_raw}, '
      f'entry-filter mismatches {bad_f}')
# the simulator: trade outcome of an entry must not depend on bars after its exit bar
R = Rep(m); days, T = R.run(full_f)
sel = T.sample(150, random_state=3)
bad = 0
for _, t in sel.iterrows():
    cut = int(t.xi) + 1
    if cut >= len(m) - 1: continue
    mt = m.iloc[:cut + 1]
    Rt = Rep(mt)
    st = entry_filter(mt, raw_signal(mt.close.values))
    st[:max(int(t.ei) - 5, 0)] = 0      # only the neighbourhood (positions open before ei can change slot use)
    st[:int(t.ei)] = np.where(np.arange(int(t.ei)) >= int(t.ei) - 5, st[:int(t.ei)], 0)
    d2, T2 = Rt.run(st)
    x = T2[(T2.ei == t.ei) & (T2.dir == t.dir)]
    if len(x) == 0 or not np.isclose(x.pnl.values[0], t.pnl):
        bad += 1
print(f'simulator truncation (data cut 1 bar after each trade exit, 150 trades): outcome mismatches {bad} '
      f'(a mismatch can also come from different slot use; 0 expected)')
