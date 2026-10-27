"""Re-run the v1.30 headline numbers without writing anything into the project (no CSV output)."""
import sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
import ea_replica_v130 as V
from mlib import Harness, SPLIT, random_like
R = V.R
t0 = time.time()
H = Harness(); tr = R.h1_trend(H.m1)
print('days: train', (H.dates < SPLIT).sum(), 'test', (H.dates >= SPLIT).sum(), H.dates[0].date(), H.dates[-1].date())
for name, kw in (('defaults', dict(spread='base', filt='bar')), ('filt base', dict(spread='base', filt='base')),
                 ('bar/bar', dict(spread='bar', filt='bar')), ('no daily', dict(daily=0.0))):
    T, S = V.run(H, tr, V.D, **kw)
    print(f'{name:10s} TRAIN', V.score(T, H.dates, 'train'))
    print(f'{"":10s} TEST ', V.score(T, H.dates, 'test'))
T, S = V.run(H, tr, V.D)
for k, g in T.groupby('module'): print('  ', k, V.score(g, H.dates, 'test'), 'n', (g.entry >= SPLIT).sum())
rnd = []
for z in range(20):
    Sr = {k: random_like(v, z * 10 + i).astype(np.int64) for i, (k, v) in enumerate(S.items())}
    Tr, _ = V.run(H, tr, V.D, S=Sr); rnd.append(V.score(Tr, H.dates, 'test')['per_day'])
rnd = np.array(rnd)
print('random test $/day sorted', np.sort(rnd))
print('median', np.median(rnd), 'best', rnd.max(), 'strategy', V.score(T, H.dates, 'test')['per_day'], 'share random >= strategy', (rnd >= V.score(T, H.dates, 'test')['per_day']).mean())
print('elapsed', round(time.time() - t0, 1))
T.to_pickle('/tmp/claude-0/-home-claude-xauusd-code/883fdbfb-6a01-54e2-a7a1-c4129201785b/scratchpad/T_default.pkl')
