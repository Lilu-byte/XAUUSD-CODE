"""Calibration on synthetic random walks (constant spread $0.205, half-cent so no level ever ties a cent tick).
Random entries must lose exactly the spread on a martingale.  Compare:
  truth_tick  : tick-exact, fill at the crossing tick (exact martingale reference)
  FAIR/OHLC/STOP/TARGET : the harness
  FAIR-truthL : paired per-trade difference vs tick-exact truth that fills at the level (same convention as the
                harness), so it isolates the error of FAIR on bars where both levels are inside the bar."""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/audit'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
import mlib
from synth import Synth

real = mlib.load_m1(); n = len(real)
K = 16900          # sigma = $1.30 per minute (real M1: mean|dC| 1.07 -> sigma ~1.34; mean range 2.05)
SPR = 0.205
mode = sys.argv[1] if len(sys.argv) > 1 else 'flat'
mu = 0.03 if mode == 'drift' else 0.0                    # $ per minute
p = 0.5 + mu / (K * 0.01) / 2
settings = [(0.1, 0.1, 5), (0.1, 1.0, 10), (0.3, 0.3, 5), (0.5, 0.5, 10), (1.0, 0.5, 10), (1.0, 0.3, 10),
            (0.5, 1.0, 10), (0.3, 1.0, 10), (1.0, 1.0, 15), (0.1, 0.5, 1), (2.0, 2.0, 30)]
sigs = ['rand'] + (['long', 'short'] if mode == 'drift' else [])
rows = []
for pseed in ((7, 8) if mode == 'flat' else (7,)):
    t0 = time.time()
    S = Synth(real, K, p=p, seed=pseed, spread_pts=SPR * 100)
    print(f'mode={mode} path seed {pseed}: built {time.time() - t0:.0f}s, mean range {(S.m1.high - S.m1.low).mean():.3f}', flush=True)
    for sname in sigs:
        sig = {'rand': np.where(np.random.default_rng(pseed * 10).random(n) < .5, 1, -1),
               'long': np.ones(n, np.int64), 'short': -np.ones(n, np.int64)}[sname]
        for mo in (1, 3):
            for tp, sl, to in settings:
                tr = S.truth(sig, tp, sl, to, mo, at_level=False)
                trL = S.truth(sig, tp, sl, to, mo, at_level=True)
                r = dict(path=pseed, sig=sname, max_open=mo, tp=tp, sl=sl, timeout=to, n=len(tr), truth_tick=tr.pnl.mean(),
                         truth_se=tr.pnl.std() / np.sqrt(len(tr)), hold_min=(tr.ticks / K).mean())
                if mode == 'drift':
                    r['expected'] = (-SPR + mu * (tr.ticks / K) * tr.dir).mean()
                for fm in ('FAIR', 'OHLC', 'STOP', 'TARGET'):
                    d, ht = S.H.run(sig, tp, sl, timeout=to, max_open=mo, fill=fm, spread='bar')
                    r[fm] = ht.pnl.mean()
                    if fm == 'FAIR':
                        aligned = len(ht) == len(trL) and np.array_equal(S.m1.index.get_indexer(ht.entry), trL.i_in.values)
                        r['aligned'] = aligned
                        if aligned:
                            dl = ht.pnl.values - trL.pnl.values
                            r['FAIR-truthL'] = dl.mean(); r['FAIR-truthL_se'] = dl.std() / np.sqrt(len(dl))
                            r['both_frac'] = (np.abs(dl) > 1e-9).mean()
                rows.append(r)
res = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(res.round(4).to_string())
res.to_csv(f'/mnt/project-files/xauusd-microscalp/audit/calib_{mode}.csv', index=False)
if mode == 'flat':
    g = res[res.max_open == 1].groupby(['tp', 'sl', 'timeout'])[['truth_tick', 'FAIR', 'OHLC', 'STOP', 'TARGET', 'FAIR-truthL', 'both_frac']].mean()
    print('\nmax_open=1, averaged over 2 synthetic paths (expected loss = 0.205):')
    print(g.round(4).to_string())
