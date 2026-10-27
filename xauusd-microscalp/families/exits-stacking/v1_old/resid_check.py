"""Is the extra loss of small-TP / wide-stop brackets (worse than the spread) a property of gold, or of the
simulator?  Same coin-flip rules on (a) real TRAIN M1 with a flat $0.20 spread and (b) a synthetic tick random walk
(audit/synth.py, flat $0.20) over the same TRAIN timestamps.  resid = per_trade + spread (0 on a martingale)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/audit')
from sigs import *
from synth import Synth

m1 = repaired_m1(); tr = m1[m1.index < SPLIT].copy()
tr['spread'] = 15.0; tr['spread_usd'] = 0.15          # base model adds 0.05 -> flat 0.20 like the synthetic
HR = Harness(tr)
S = Synth(tr, 16900, p=0.5, seed=11)
n = len(tr)
rows = []
for tp, sl, to in [(0.1, 20, 30), (0.1, 5, 30), (0.3, 5, 30), (0.3, 1, 10), (0.5, 0.5, 10), (1.0, 0.3, 10), (1.0, 20, 30)]:
    for seed in range(2):
        sig = np.where(np.random.default_rng(900 + seed).random(n) < .5, 1, -1)
        tre = run_pw(HR, sig, tp, sl, timeout=to)[1]
        sy = run_pw(S.H, sig, tp, sl, timeout=to, spread='bar')[1]
        tru = S.truth(sig, tp, sl, to, 1)
        rows.append(dict(bracket=f'{tp}/{sl}/{to}', seed=seed, real_resid=tre.pnl.mean() + 0.20,
                         real_long=tre.pnl[tre.dir == 1].mean() + .2, real_short=tre.pnl[tre.dir == -1].mean() + .2,
                         synth_FAIR_resid=sy.pnl.mean() + 0.20, synth_tick_truth_resid=tru.pnl.mean() + 0.20,
                         real_win=tre.pwin.mean(), synth_win=sy.pwin.mean()))
R = pd.DataFrame(rows).groupby('bracket').mean(numeric_only=True).drop(columns='seed')
pd.set_option('display.width', 200)
print(R.round(3).to_string())
R.to_csv(OUT + 'resid_check_train.csv')
