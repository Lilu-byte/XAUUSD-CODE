"""Look-ahead check for the M5 feature builder (truncate at t, compare row t)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from feat5 import *
d = load('M5'); cache = {tf: load(tf) for tf in ('M15', 'H1', 'H4')}
F = build5(d, cache); print(F.shape)
bad = 0
for t in np.random.default_rng(1).integers(5000, len(d) - 5, 8):
    Fs = build5(d.iloc[:t + 1], cache)
    a = F.iloc[t - 2:t + 1].values.astype(float); b = Fs.iloc[-3:].values.astype(float)
    diff = np.nanmax(np.abs(a - b) / (np.abs(a) + 1e-3), axis=0); nm = (np.isnan(a) != np.isnan(b)).any(axis=0)
    bc = [F.columns[j] for j in range(F.shape[1]) if diff[j] > 1e-3 or nm[j]]; bad += len(bc)
    print(d.index[t], bc)
print('TOTAL mismatches', bad)
