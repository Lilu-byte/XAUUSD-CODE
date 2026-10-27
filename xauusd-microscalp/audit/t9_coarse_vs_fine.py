"""Test the fill models on REAL price paths: run the same coin-flip trades on M5 bars (built from M1) and on the
M1 bars inside them. M1 resolves most of what is ambiguous at M5, so (M5 result - M1 result) estimates the error
of a fill model on real (non-Brownian) intrabar paths at a 5x coarser scale. Brackets scaled by ~sqrt(5)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/audit'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
import mlib
from synth import Synth


def coarse_vs_fine(m1, label, spr=0.205):
    n = len(m1)
    key = m1.index.floor('5min')
    cnt = pd.Series(1, index=m1.index).groupby(key).transform('size').values
    pos = pd.Series(np.arange(n), index=m1.index).groupby(key).cumcount().values
    full_last = (cnt == 5) & (pos == 4)                       # last M1 bar of a complete M5 bar
    g = m1.groupby(key)
    m5 = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(), 'close': g.close.last(),
                       'tick_volume': g.tick_volume.sum(), 'spread': spr * 100})
    m5['spread_usd'] = spr; m5['tod'] = m5.index.hour * 60 + m5.index.minute
    m1c = m1.copy(); m1c['spread'] = spr * 100; m1c['spread_usd'] = spr
    H1, H5 = mlib.Harness(m1c), mlib.Harness(m5)
    m5_full = pd.Series(cnt == 5, index=m1.index).groupby(key).first().reindex(m5.index).values
    rows = []
    for tp, sl, to5 in [(0.7, 0.7, 2), (1.1, 1.1, 2), (2.2, 1.1, 2), (2.2, 0.7, 2), (1.1, 2.2, 2), (2.2, 2.2, 3)]:
        for seed in range(3):
            r5 = np.random.default_rng(700 + seed).random(len(m5))
            s5 = np.where(r5 < .5, 1, -1) * m5_full
            # M1 signal at the last M1 bar of each complete M5 bar
            m5_pos = m5.index.get_indexer(key[full_last])
            s1 = np.zeros(n, np.int64); s1[np.where(full_last)[0]] = s5[m5_pos]
            out5 = {fm: H5.run(s5, tp, sl, timeout=to5, fill=fm, spread='bar')[1] for fm in ('FAIR', 'OHLC')}
            _, t1 = H1.run(s1, tp, sl, timeout=5 * to5, fill='FAIR', spread='bar')
            t5 = out5['FAIR']
            aligned = len(t5) == len(t1) and np.array_equal(t5.entry.values + np.timedelta64(4, 'm'), t1.entry.values)
            rows.append(dict(data=label, set=f'{tp}/{sl}/{to5}x5m', seed=seed, n=len(t1), aligned=aligned,
                             M1_resolved=t1.pnl.mean() + spr, M5_FAIR=t5.pnl.mean() + spr, M5_OHLC=out5['OHLC'].pnl.mean() + spr))
    return pd.DataFrame(rows)


real = mlib.load_m1()
R = [coarse_vs_fine(real, 'real')]
S = Synth(real, 16900, p=0.5, seed=31, spread_pts=20.5)
R.append(coarse_vs_fine(S.m1, 'synth'))
R = pd.concat(R)
print('aligned all:', R.aligned.all())
G = R.groupby(['set', 'data'])[['M1_resolved', 'M5_FAIR', 'M5_OHLC']].mean()
G['FAIR_err'] = G.M5_FAIR - G.M1_resolved; G['OHLC_err'] = G.M5_OHLC - G.M1_resolved
pd.set_option('display.width', 200)
print('residual per trade = pnl + spread (0 = fair on a martingale); err = M5 fill model minus M1-resolved')
print(G.round(4).unstack('data').to_string())
