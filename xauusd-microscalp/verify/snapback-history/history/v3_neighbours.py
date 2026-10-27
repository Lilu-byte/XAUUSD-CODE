"""Step 3: one-step neighbours of pick C on M15 (each parameter moved one step either way, the rest fixed),
on and off the colleague's grid, plus a 2-D k x N map. TRAIN = 2022-07..2024-12, TEST = 2025-01..2026-10-09."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history')
from vlib import *
OUT = '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/'
d = load('M15'); E = Eng(d, 15)
P = {'TRAIN': ('2022-07-01', '2025-01-01'), 'TEST': ('2025-01-01', None), 'TEST_CLEAN': ('2025-01-01', '2026-06-26'), 'M1ERA': ('2026-06-26', None)}
base = dict(n=2, k=4.0, gate=1, N=2, sl=25, mo=3, L=32)
steps = {'n': [1, 3], 'k': [3.0, 3.5, 4.5, 5.0], 'gate': [0], 'N': [1, 3, 4], 'sl': [10, 15, 40, 1000], 'mo': [1, 2, 5], 'L': [16, 24, 48, 64]}
fcache = {}
def run(cfg, rand_seeds=0):
    L = cfg['L']
    if L not in fcache: fcache[L] = features(d, 15, L=L)[0]
    s = signal(d, fcache[L], cfg['n'], cfg['k'], cfg['gate'])
    days, T = E.run(s, cfg['N'], cfg['sl'], cfg['mo'])
    out = {}
    for p, (lo, hi) in P.items():
        st = stats(days, T, lo, hi); out[p] = st
    if rand_seeds:
        idx = np.where(s != 0)[0]; rg = np.random.default_rng(1)
        for p, (lo, hi) in P.items():
            out[p]['rand'] = []
        for z in range(rand_seeds):
            r = np.zeros(len(s)); r[idx] = np.where(rg.random(len(idx)) < .5, 1, -1)
            dr, Tr = E.run(r, cfg['N'], cfg['sl'], cfg['mo'])
            for p, (lo, hi) in P.items(): out[p]['rand'].append(stats(dr, Tr, lo, hi)['per_day'])
    return out
rows = []; nconf = 0
def show(label, cfg):
    global nconf
    nconf += 1
    o = run(cfg, rand_seeds=20)
    rows.append(dict(label=label, **cfg, **{f'{p}_{m}': o[p][m] for p in P for m in ('per_day', 'per_trade', 'trades', 'tstat', 'worst_day')},
                     **{f'{p}_rand': np.mean(o[p]['rand']) for p in P}))
    print(f'{label:12s} ' + ' | '.join(f"{p} {o[p]['per_day']:+.3f}/d {o[p]['per_trade']:+.2f}/tr t{o[p]['tstat']:+.2f} n{o[p]['trades']} r{np.mean(o[p]['rand']):+.2f}" for p in P), flush=True)
show('PICK', base)
for k_, vals in steps.items():
    for v in vals:
        c = dict(base); c[k_] = v; show(f'{k_}={v}', c)
# 2-D map k x N (TRAIN | TEST $/day)
print('\nk x N map, $/day TRAIN | TEST | M1ERA (n=2, gate=1, sl=25, mo=3, L=32)')
for k_ in (3.0, 3.5, 4.0, 4.5, 5.0, 6.0):
    line = []
    for N in (1, 2, 3, 4, 6):
        c = dict(base, k=k_, N=N); o = run(c); nconf += 1
        rows.append(dict(label='map', **c, **{f'{p}_{m}': o[p][m] for p in P for m in ('per_day', 'per_trade', 'trades', 'tstat', 'worst_day')}))
        line.append(f"N{N}: {o['TRAIN']['per_day']:+.2f}|{o['TEST']['per_day']:+.2f}|{o['M1ERA']['per_day']:+.2f}")
    print(f'  k{k_}: ' + '  '.join(line), flush=True)
R = pd.DataFrame(rows); R.to_csv(OUT + 'neighbours.csv', index=False)
nb = R[(R.label != 'PICK') & (R.label != 'map')]
print(f'\none-step neighbours: {len(nb)}; positive TRAIN {int((nb.TRAIN_per_day > 0).sum())}, positive TEST {int((nb.TEST_per_day > 0).sum())}, '
      f'positive both {int(((nb.TRAIN_per_day > 0) & (nb.TEST_per_day > 0)).sum())}, positive M1ERA {int((nb.M1ERA_per_day > 0).sum())}; '
      f'median TRAIN {nb.TRAIN_per_day.median():+.3f} TEST {nb.TEST_per_day.median():+.3f}')
mp = R[R.label == 'map']
print(f'k x N map: {len(mp)} cells; positive TRAIN {int((mp.TRAIN_per_day > 0).sum())}, TEST {int((mp.TEST_per_day > 0).sum())}, M1ERA {int((mp.M1ERA_per_day > 0).sum())}')
print('configurations scored in this step:', nconf)
