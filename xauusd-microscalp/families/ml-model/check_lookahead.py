"""Look-ahead check: features at row t computed from data truncated at t must equal the full-data features."""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from feat import *
from mlib import load_m1

m1 = load_m1()
cache = {tf: load(tf) for tf in ('M5', 'M15', 'H1', 'H4')}
t0 = time.time(); F = build(m1, cache); print('build', round(time.time() - t0, 1), 's', F.shape)
rng = np.random.default_rng(0)
bad = 0
for t in rng.integers(2000, len(m1) - 10, 8):
    sub = m1.iloc[:t + 1]
    Fs = build(sub, cache)
    a = F.iloc[t - 3:t + 1].values.astype(float); b = Fs.iloc[-4:].values.astype(float)
    diff = np.nanmax(np.abs(a - b) / (np.abs(a) + 1e-3), axis=0)
    nanmis = (np.isnan(a) != np.isnan(b)).any(axis=0)
    badc = [F.columns[j] for j in range(F.shape[1]) if diff[j] > 1e-3 or nanmis[j]]
    print(m1.index[t], 'mismatching cols:', badc)
    bad += len(badc)
print('TOTAL mismatches', bad)
print('NaN share (after first 2000 rows):'); na = F.iloc[2000:].isna().mean(); print(na[na > 0].round(3).to_dict())
