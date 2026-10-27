"""Where (in time) is the real-data coin-flip residual earned? Variance ratios of M1 bid closes."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd, mlib
m1 = mlib.load_m1(); H = mlib.Harness(m1); n = len(m1)
H._spr['c205'] = np.full(n, 0.205)
c = m1.close.values
for k in (1, 2, 5, 15):
    r1 = np.diff(c); rk = c[k:] - c[:-k]
    print(f'variance ratio VR({k}) = {rk.var() / (k * r1.var()):.3f}')
r1 = pd.Series(np.diff(c))
print('lag-1 autocorr of M1 close changes: %.4f; excluding |r|>5: %.4f' % (r1.autocorr(), r1[r1.abs() < 5].autocorr()))
rows = []
for seed in range(6):
    sig = np.where(np.random.default_rng(40 + seed).random(n) < .5, 1, -1)
    _, tr = H.run(sig, 1.0, 0.5, timeout=10, fill='FAIR', spread='c205')
    tr['res'] = tr.pnl + 0.205
    ii = m1.index.get_indexer(tr.entry); io = ii + tr.bars.values
    tr = tr[H.day[io] == H.day[ii]]
    tr['hour'] = tr.entry.dt.hour; tr['month'] = tr.entry.dt.month
    rows.append(tr)
T = pd.concat(rows)
print('TP1.0/SL0.5/10, coin flip, const spread .205: overall residual %.4f (n=%d)' % (T.res.mean(), len(T)))
print('by hour:', T.groupby('hour').res.mean().round(3).to_dict())
print('by month:', T.groupby('month').res.mean().round(3).to_dict())
print('by dir:', T.groupby('dir').res.mean().round(4).to_dict())
mask = (T.entry.dt.hour >= 2) & (T.entry.dt.hour < 22)
print('excluding 01:xx and 22:xx: %.4f' % T.res[mask].mean())
