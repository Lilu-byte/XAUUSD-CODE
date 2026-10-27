"""Look-ahead check: every final-candidate signal computed on data truncated at bar n must equal the
full-data signal on bars < n (a signal at bar i may only use bars <= i). Also checks the forming-M5
sweep and the M5-placed signals from the scans."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from cands import *
from base_sigs import build_base
from mlib import Harness, load_m1
m1 = load_m1()
full = build2(m1); full.update(build(m1))
class _H: pass
Hf = _H(); Hf.m1 = m1; Hf.day = np.unique(m1.index.normalize().values, return_inverse=True)[1]
fb = build_base(Hf)
bad = 0
for n in (20011, 45678, 70001, 99000):
    mt = m1.iloc[:n]
    t = build2(mt); t.update(build(mt))
    Ht = _H(); Ht.m1 = mt; Ht.day = np.unique(mt.index.normalize().values, return_inverse=True)[1]
    tb = build_base(Ht)
    for k in t:
        d = (t[k][:n - 1] != full[k][:n - 1]).sum()      # last bar may lack its HTF close in truncated data
        if d: bad += 1; print('MISMATCH', n, k, d)
    for k in tb:
        d = (tb[k][:n - 6] != fb[k][:n - 6]).sum()
        if d: bad += 1; print('MISMATCH base', n, k, d)
print('look-ahead check done; mismatching signals:', bad)

# filters used in scan2/scan3
bad2 = 0
F_full = {'m15': trend_m15(m1), 'h1': trend_h1(m1), 'vol': vol_regime(m1)}
for n in (20011, 45678, 70001, 99000):
    mt = m1.iloc[:n]
    Ft = {'m15': trend_m15(mt), 'h1': trend_h1(mt), 'vol': vol_regime(mt)}
    Ht = _H(); Ht.m1 = mt; Ht.day = np.unique(mt.index.normalize().values, return_inverse=True)[1]
    tb = build_base(Ht)
    for k in Ft:
        d = (np.asarray(Ft[k])[:n] != np.asarray(F_full[k])[:n]).sum()
        if d: bad2 += 1; print('FILTER MISMATCH', n, k, d)
    for k in tb:
        d = (tb[k] != fb[k][:n]).sum()
        if d: bad2 += 1; print('MISMATCH base (all rows)', n, k, d)
print('filter / all-row check done; mismatches:', bad2)
