"""(1) run_pw == mlib v2 Harness.run on TRAIN rows; (2) look-ahead check of sigs2.build: rebuild every signal from
data known at random cut times T (M1 rows <= T, HTF bars closed by T's close) and compare with the full build."""
import sigs2
from sigs2 import *

m1, H = train_harness()
cf = np.where(np.random.default_rng(1).random(len(H.m1)) < .5, 1, -1)
print('run_pw vs mlib.Harness.run mismatching configs:', check_equal(H, cf))
full = build(m1)
rng = np.random.default_rng(3); bad = 0; checked = 0
cuts = rng.choice(np.arange(5000, len(m1) - 10), 25, replace=False)
orig = {tf: load(tf) for tf in ('M5', 'M15', 'H1')}
for ci in cuts:
    T = m1.index[ci]
    sub = m1.iloc[:ci + 1]
    sigs2._TF.clear()
    for tf, d in orig.items():
        sigs2._TF[tf] = d[d.index + pd.Timedelta(minutes=MIN[tf]) <= T + pd.Timedelta(minutes=1)]
    part = build(sub)
    for k in full:
        if k == 'CF': continue
        checked += 1
        if not np.array_equal(full[k][ci - 300:ci + 1], part[k][ci - 300:ci + 1]): bad += 1; print('MISMATCH', k, T)
print('look-ahead: checked', checked, 'mismatches', bad)
