"""Heteroskedastic synthetic random walk: each synthetic M1 bar gets the volatility implied by the real bar's
range (K_i ticks of $0.01), so bar-range distribution and volatility clustering resemble the real data.
Compare harness FAIR on (a) real data, (b) this synthetic, (c) tick-exact truth; constant spreads, coin-flip entries."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/audit'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
import mlib
from synth import Synth

real = mlib.load_m1(); n = len(real); HR = mlib.Harness(real)
rng_ = (real.high - real.low).values
K = np.clip(np.round((rng_ / 1.596 / 0.01) ** 2), 25, 400000).astype(np.int64)
S = Synth(real, K, p=0.5, seed=21, spread_pts=20.5)
print('synthetic mean range %.3f (real %.3f); median %.3f (real %.3f)' % (
    (S.m1.high - S.m1.low).mean(), rng_.mean(), (S.m1.high - S.m1.low).median(), np.median(rng_)))
rows = []
for tp, sl, to in [(0.3, 0.3, 5), (0.5, 0.5, 10), (1.0, 0.5, 10), (1.0, 0.3, 10), (0.5, 1.0, 10), (0.3, 1.0, 10), (1.0, 1.0, 15)]:
    for seed in range(3):
        sig = np.where(np.random.default_rng(900 + seed).random(n) < .5, 1, -1)
        _, hs = S.H.run(sig, tp, sl, timeout=to, fill='FAIR', spread='bar')
        _, ho = S.H.run(sig, tp, sl, timeout=to, fill='OHLC', spread='bar')
        tr = S.truth(sig, tp, sl, to, 1, at_level=False)
        trL = S.truth(sig, tp, sl, to, 1, at_level=True)
        # real data with a constant spread of $0.205 (custom spread array via 'wide' slot)
        HR._spr['c205'] = np.full(n, 0.205)
        _, hr = HR.run(sig, tp, sl, timeout=to, fill='FAIR', spread='c205')
        ii = real.index.get_indexer(hr.entry); io = ii + hr.bars.values
        ok = HR.day[io] == HR.day[ii]
        al = len(hs) == len(trL) and np.array_equal(S.m1.index.get_indexer(hs.entry), trL.i_in.values)
        rows.append(dict(set=f'{tp}/{sl}/{to}', seed=seed, synth_truth=tr.pnl.mean() + 0.205, synth_FAIR=hs.pnl.mean() + 0.205,
                         synth_OHLC=ho.pnl.mean() + 0.205,
                         FAIR_minus_truthL=(hs.pnl.values - trL.pnl.values).mean() if al else np.nan,
                         real_FAIR=hr.pnl[ok].mean() + 0.205))
R = pd.DataFrame(rows).groupby('set').mean().drop(columns='seed')
pd.set_option('display.width', 200)
print('residual per trade = pnl + 0.205 (0 = fair on a martingale)')
print(R.round(4).to_string())
