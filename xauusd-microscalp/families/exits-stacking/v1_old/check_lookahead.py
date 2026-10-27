"""Look-ahead check: rebuild every signal using only data known at random cut times T (M1 rows <= T and HTF bars
that had closed by T's close) and compare with the full-data signal on the rows <= T."""
import sigs
from sigs import *

m1 = load_m1(); full = build(m1)
rng = np.random.default_rng(3); bad = 0; checked = 0
cuts = rng.choice(np.arange(5000, len(m1) - 10), 25, replace=False)
orig = {tf: load(tf) for tf in ('M5', 'M15', 'H1')}
for ci in cuts:
    T = m1.index[ci]
    sub = m1.iloc[:ci + 1]
    sigs._TF.clear()
    for tf, d in orig.items():   # only HTF bars that closed by the close of bar T
        sigs._TF[tf] = d[d.index + pd.Timedelta(minutes=MIN[tf]) <= T + pd.Timedelta(minutes=1)]
    part = build(sub)
    for k in full:
        if k == 'CF': continue
        a = full[k][ci - 300:ci + 1]; b = part[k][ci - 300:ci + 1]
        checked += 1
        if not np.array_equal(a, b): bad += 1; print('MISMATCH', k, T)
print('checked', checked, 'mismatches', bad)
