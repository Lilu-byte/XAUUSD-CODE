"""Sanity checks for gridsim (TRAIN rows only):
1) maxlev=1 grid == single bracket: compare with mlib-style run_pw (FAIR) on the same coin-flip signal.
2) On a synthetic tick random walk (audit/synth.py, flat $0.20 spread) any grid should lose ~ spread x positions."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/audit')
from sigs import *
from gridsim import *
from synth import Synth

m1 = repaired_m1(); tr = m1[m1.index < SPLIT]
H = Harness(tr); n = len(tr)
cf = np.where(np.random.default_rng(5).random(n) < .5, 1, -1)
print('1) single-position check  (grid maxlev=1 vs bracket sim), per trade:')
for T, S, to in [(0.3, 0.3, 10), (0.1, 1.0, 10), (1.0, 5.0, 30), (0.5, 20.0, 30)]:
    d, t = run_pw(H, cf, T, S, timeout=to)
    g = [run_grid(H, cf, 1.0, 1, T, S, tmax=to, seed=s) for s in range(3)]
    pb = np.mean([x[1].pnl.mean() for x in g]); nb = np.mean([len(x[1]) for x in g])
    print(f'   tp {T} sl {S} to {to}: bracket {t.pnl.mean():.3f} ({len(t)} trades)  grid {pb:.3f} ({nb:.0f} baskets)'
          f'  OHLC-path grid {run_grid(H, cf, 1.0, 1, T, S, tmax=to, path="OHLC")[1].pnl.mean():.3f}')

trs = tr.copy(); trs['spread'] = 15.0; trs['spread_usd'] = 0.15
Sy = Synth(trs, 16900, p=0.5, seed=21)
print('2) synthetic random walk, flat spread 0.20: per_position should be ~ -0.20')
for dirn in ('long', 'cf'):
    sig = np.ones(n) if dirn == 'long' else cf
    for step, L, T, S in [(1.0, 10, 0.3, 0), (0.5, 50, 0.1, 0), (2.0, 5, 1.0, 50), (3.0, 20, 0.5, 0)]:
        res = [run_grid(Sy.H, sig, step, L, T, S, seed=s, spread='bar') for s in range(3)]
        pp = np.mean([x[0].pnl.sum() / x[0].positions.sum() for x in res])
        bw = np.mean([(x[1].pnl > 0).mean() for x in res])
        print(f'   {dirn:4s} step {step} lev {L} btp {T} bsl {S}: per_position {pp:.3f}  basket win {bw:.3f}  '
              f'per_day {np.mean([x[0].pnl.mean() for x in res]):.1f}')
