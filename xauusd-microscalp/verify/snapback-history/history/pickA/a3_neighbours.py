"""Step 3: multiple testing.
 (a) one-step neighbours of pick A (each parameter one step either way, others fixed), TRAIN / TEST / sub-periods
 (b) selection null: run the colleague's 144-setting M15 grid with RANDOM directions (same random direction per bar
     across settings, 50 seeds), pick the best TRAIN $/day as the colleague did, and see what TRAIN $/day the luckiest
     setting reaches and what it then does on TEST."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickA')
from alib import *
OUT = '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickA/'
P = {'TRAIN': ('2022-07-01', '2025-01-01'), 'TRAIN_H1': ('2022-07-01', '2023-10-01'), 'TRAIN_H2': ('2023-10-01', '2025-01-01'),
     'TEST': ('2025-01-01', None), 'TEST_PRE_M1': ('2025-01-01', '2026-06-26'), 'M1ERA': ('2026-06-26', None)}
d = finish(read('M15')); E = Eng(d, 15)
base = dict(n=2, k=4.0, gate=True, N=4, sl=25, mo=3, L=32)
steps = {'n': (1, 3), 'k': (3.0, 3.5, 4.5, 5.0), 'gate': (False,), 'N': (2, 3, 5, 6), 'sl': (10, 15, 40, 1000), 'mo': (1, 2, 5), 'L': (16, 24, 48, 64)}
cfgs = [('PICK', base)] + [(f'{p}={v}', {**base, p: v}) for p, vs in steps.items() for v in vs]
fc = {}
rows = []
print(f'{"setting":10s} ' + ' | '.join(f'{p}' for p in ('TRAIN', 'TRAIN_H1', 'TRAIN_H2', 'TEST', 'TEST_PRE_M1', 'M1ERA')) + '   ($/day [$/tr, t] ; TEST random share>=)')
for name, c in cfgs:
    key = (c['n'], c['L'])
    if key not in fc: fc[key] = features(d, 15, w=1, L=c['L'], n=c['n'])
    s = signal(d, fc[key], c['k'], c['gate'])
    days, T = E.run(s, c['N'], c['sl'], c['mo'])
    R = [E.run(rand_dirs(s, z), c['N'], c['sl'], c['mo']) for z in range(20)]
    parts = []; r = dict(setting=name, **{k: v for k, v in c.items()})
    for p, (lo, hi) in P.items():
        st = stats(days, T, lo, hi)
        rp = np.array([stats(a, b, lo, hi)['per_day'] for a, b in R])
        r[f'{p}_per_day'] = st['per_day']; r[f'{p}_per_trade'] = st['per_trade']; r[f'{p}_t'] = st['tstat']
        r[f'{p}_trades'] = st['trades']; r[f'{p}_rand_share'] = (rp >= st['per_day']).mean()
        parts.append(f"{st['per_day']:+.2f} [{st['per_trade']:+.2f},{st['tstat']:+.1f}]")
    rows.append(r)
    print(f'{name:10s} ' + ' | '.join(parts) + f"  ; {r['TEST_rand_share']:.2f}", flush=True)
N_ = pd.DataFrame(rows); N_.to_csv(OUT + 'neighbours.csv', index=False)
nb = N_[N_.setting != 'PICK']
print(f"neighbours ({len(nb)}): TRAIN positive {int((nb.TRAIN_per_day > 0).sum())}, both TRAIN halves positive "
      f"{int(((nb.TRAIN_H1_per_day > 0) & (nb.TRAIN_H2_per_day > 0)).sum())}, TEST positive {int((nb.TEST_per_day > 0).sum())}, "
      f"TEST_PRE_M1 positive {int((nb.TEST_PRE_M1_per_day > 0).sum())}, M1ERA positive {int((nb.M1ERA_per_day > 0).sum())}, "
      f"TRAIN t > 2: {int((nb.TRAIN_t > 2).sum())}, TEST t > 2: {int((nb.TEST_t > 2).sum())}")

# (b) selection null on the colleague's grid
grid = [(n, k, g, N, sl, mo) for n in (1, 2) for k in (2.5, 3, 4) for g in (0, 1) for N in (1, 2, 4) for sl in (10, 25) for mo in (1, 3)]
sigs = {}
for n in (1, 2):
    f = features(d, 15, w=1, L=32, n=n)
    for k in (2.5, 3, 4):
        for g in (0, 1): sigs[(n, k, g)] = signal(d, f, k, bool(g))
best = []
for z in range(50):
    rd = np.where(np.random.default_rng(1000 + z).random(len(d)) < .5, 1.0, -1.0)
    res = []
    for (n, k, g, N, sl, mo) in grid:
        s = np.where(sigs[(n, k, g)] != 0, rd, 0.0)
        days, T = E.run(s, N, sl, mo)
        res.append((stats(days, T, *P['TRAIN'])['per_day'], stats(days, T, *P['TEST'])['per_day']))
    res = np.array(res); j = res[:, 0].argmax()
    best.append((res[j, 0], res[j, 1], (res[:, 0] > 0).mean(), (res[:, 1] > 0).mean()))
B = np.array(best)
print(f'selection null (50 seeds x 144 settings, random directions): best-of-144 TRAIN $/day mean {B[:, 0].mean():+.3f}, '
      f'median {np.median(B[:, 0]):+.3f}, 90th pct {np.quantile(B[:, 0], .9):+.3f}, share of seeds whose best >= pick (+0.236): '
      f'{(B[:, 0] >= 0.236).mean():.2f}; that best setting on TEST: mean {B[:, 1].mean():+.3f}, share >= +0.826: {(B[:, 1] >= 0.826).mean():.2f}; '
      f'share of settings positive per seed: TRAIN {B[:, 2].mean():.2f}, TEST {B[:, 3].mean():.2f}')
pd.DataFrame(B, columns=['best_train', 'its_test', 'share_pos_train', 'share_pos_test']).to_csv(OUT + 'selection_null.csv', index=False)
