"""Where does the real-data residual (pnl + spread paid) come from?  Split trades into 'both levels inside one
bar' (fill-model dependent) vs the rest, on real data and on the synthetic random walk (with tick truth)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/audit'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
import mlib
from synth import Synth

real = mlib.load_m1(); HR = mlib.Harness(real); n = len(real)
S = Synth(real, 16900, p=0.5, seed=7)
settings = [(0.3, 0.3, 5), (0.5, 0.5, 10), (1.0, 0.5, 10), (1.0, 0.3, 10), (0.5, 1.0, 10), (1.0, 1.0, 15)]
rows = []
for tp, sl, to in settings:
    for name, H in (('real', HR), ('synth', S.H)):
        for seed in range(3):
            sig = np.where(np.random.default_rng(500 + seed).random(n) < .5, 1, -1)
            sp = 'wide' if name == 'real' else 'bar'          # constant spread (0.30 real, 0.20 synthetic)
            out = {fm: H.run(sig, tp, sl, timeout=to, fill=fm, spread=sp)[1] for fm in ('FAIR', 'STOP', 'TARGET')}
            f = out['FAIR']
            ii = H.m1.index.get_indexer(f.entry); io = ii + f.bars.values
            ok = H.day[io] == H.day[ii]
            spr = H._spr[sp]; paid = np.where(f.dir == 1, spr[ii], spr[io])
            res = f.pnl.values + paid
            both = np.abs(out['TARGET'].pnl.values - out['STOP'].pnl.values) > 1e-9
            r = dict(set=f'{tp}/{sl}/{to}', data=name, seed=seed, resid=res[ok].mean(),
                     both_frac=both[ok].mean(), resid_both=res[ok & both].sum() / ok.sum(), resid_rest=res[ok & ~both].sum() / ok.sum())
            if name == 'synth':
                tr = S.truth(sig, tp, sl, to, 1)
                tres = tr.pnl.values + 0.2
                r['truth_resid'] = tres[ok].mean()
                r['truth_both'] = tres[ok & both].sum() / ok.sum(); r['truth_rest'] = tres[ok & ~both].sum() / ok.sum()
            rows.append(r)
R = pd.DataFrame(rows).groupby(['set', 'data']).mean(numeric_only=True).drop(columns='seed')
pd.set_option('display.width', 200)
print('contributions per trade (sum over subset / all trades); resid = resid_both + resid_rest')
print(R.round(4).to_string())
