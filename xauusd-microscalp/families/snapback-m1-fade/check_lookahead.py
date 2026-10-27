"""Truncation test: the signal (and the ladder's pre-spike level) at bar i must not change when the data is cut right
after bar i. 400 random bars over the whole M1 file (TRAIN and TEST), for every pick's signal and a few others."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from sb import *
from picks import PICKS
m = load_m1()
f = feats(m)
defs = {k: p['sig'] for k, p in PICKS.items()}
defs.update({'r1_atr3_away': (1, 'atr', 3.0, 'away', False, 0.0), 'r2_usd5_fresh': (2, 'usd', 5.0, 'none', True, 0.0)})
full = {k: fade_signal(f, *d) for k, d in defs.items()}
rng = np.random.default_rng(1)
idx = rng.choice(np.arange(300, len(m) - 1), 400, replace=False)
bad = {k: 0 for k in defs}; badl = 0; nz = {k: 0 for k in defs}
for i in idx:
    mt = m.iloc[:i + 1]
    ft = feats(mt)
    for k, d in defs.items():
        st = fade_signal(ft, *d)
        bad[k] += int(st[-1] != full[k][i]); nz[k] += int(full[k][i] != 0)
    badl += int(not np.isclose(ft.p3.values[-1], f.p3.values[i]))
print('truncation test on', len(idx), 'random bars:')
for k in defs: print(f'  {k:26s} mismatches {bad[k]}  (non-zero signals among the tested bars: {nz[k]})')
print('  pre-spike level close[i-3] mismatches', badl)
# targeted: also test bars where a pick signal fires (so non-zero signals are covered)
for k in PICKS:
    on = np.flatnonzero(full[k] != 0); on = on[on > 300]
    sel = rng.choice(on, min(100, len(on)), replace=False); b = 0
    for i in sel:
        ft = feats(m.iloc[:i + 1]); b += int(fade_signal(ft, *defs[k])[-1] != full[k][i])
    print(f'  {k:26s} on 100 bars where it fires: mismatches {b}')
