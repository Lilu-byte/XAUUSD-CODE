import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/audit'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd, mlib
from synth import Synth
real = mlib.load_m1(); n = len(real)
S = Synth(real, 16900, p=0.5, seed=7)
sig = np.where(np.random.default_rng(500).random(n) < .5, 1, -1)
tp, sl, to = 1.0, 0.5, 10
out = {fm: S.H.run(sig, tp, sl, timeout=to, fill=fm, spread='bar')[1] for fm in ('FAIR', 'STOP', 'TARGET')}
tr = S.truth(sig, tp, sl, to, 1)
f = out['FAIR']
print(len(f), len(tr), np.array_equal(S.m1.index.get_indexer(f.entry), tr.i_in.values))
both = np.abs(out['TARGET'].pnl.values - out['STOP'].pnl.values) > 1e-9
d = f.pnl.values - tr.pnl.values
print('rest: max|diff|', np.abs(d[~both]).max(), 'mean diff', d[~both].mean(), 'n diff>1e-6', (np.abs(d[~both]) > 1e-6).sum())
k = np.where((~both) & (np.abs(d) > 1e-6))[0][:5]
print(pd.DataFrame({'h_pnl': f.pnl.values[k], 't_pnl': tr.pnl.values[k], 'bars': f.bars.values[k], 'tbars': (tr.i_out - tr.i_in).values[k], 'dir': f.dir.values[k]}))
print('both: mean diff', d[both].mean(), ' n', both.sum())
