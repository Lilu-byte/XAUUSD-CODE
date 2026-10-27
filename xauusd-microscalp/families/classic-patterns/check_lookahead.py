"""Truncation test: signals at rows <= cut must not change when later data is removed."""
from pats import *
H = Harness(); m = H.m1
rng = np.random.default_rng(0)
cuts = rng.integers(5000, len(m) - 100, 6)
for k in (1, 2, 3):
    full = on_m1(m, k)
    bad = 0
    for cut in cuts:
        part = on_m1(m.iloc[:cut + 1], k)
        for n in full:
            bad += (full[n][:cut + 1] != part[n]).sum()
    print('k', k, 'mismatches', bad, 'patterns', len(full))
for tf in ('M15', 'H1'):
    t = trend(m, tf)
    print(tf, 'trend share +1', (t > 0).mean().round(3), 'zeros', (t == 0).sum())
