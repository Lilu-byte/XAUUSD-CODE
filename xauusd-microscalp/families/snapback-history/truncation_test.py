"""Look-ahead check: recompute every signal on data cut right after bar i (300 random i per TF); expect 0 mismatches."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-history')
from hlib import *
rng = np.random.default_rng(7)
tot = 0; bad = 0
for tf in ('M5', 'M15'):
    d = load_tf(tf); f = features(d, tf)
    full = {(n, k, g): signal(d, f, n, k, g) for n in (1, 2) for k in (2.5, 3, 4) for g in (0, 1)}
    for i in rng.integers(200, len(d) - 1, 300):
        dc = d.iloc[:i + 1]; fc = features(dc, tf)
        for key, s in full.items():
            sc = signal(dc, fc, *key)
            tot += 1; bad += int(sc[i] != s[i])
print(f'truncation test: {tot} (bar, rule) checks, {bad} mismatches')
