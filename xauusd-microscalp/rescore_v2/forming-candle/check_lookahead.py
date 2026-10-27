"""Truncation test: signals computed on data cut at bar j must equal full-data signals for rows <= j."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from sigs import *
m1 = load_m1(); X = build(m1)
def all_sigs(m, X):
    bs = m.spread_usd.values; hr = m.index.hour.values
    a = np.where((hr >= 15) & (hr <= 19), first_minute_break_fade(X, 'f15', (1,), 'close', 0.1), 0)
    b = np.where(bs <= 0.10, first_minute_break_fade(X, 'f15', (1,), 'close', 0.1), 0)
    c = np.where((hr >= 15) & (hr <= 19), strong_close_fade(X, 'f15', 0.8, 0.9, (14, 15)), 0)
    return np.vstack([a, b, c])
full = all_sigs(m1, X)
rng = np.random.default_rng(0)
bad = 0
for j in rng.integers(2000, len(m1) - 10, 12):
    mt = m1.iloc[:j + 1]
    St = all_sigs(mt, build(mt))
    d = (St != full[:, :j + 1]).sum()
    bad += d
    print(j, m1.index[j], 'mismatches:', d, ' nonzero signals so far:', (St != 0).sum(axis=1))
print('TOTAL mismatches', bad)
