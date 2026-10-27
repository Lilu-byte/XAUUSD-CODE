"""Post-hoc tail-risk analysis of the frozen grid pick B (no new configuration is evaluated on TEST; this only
re-reads pick B's own baskets): basket depth tail, adverse excursion, break-even failure rate, account survival."""
from sigs2 import *
from gridsim2 import *

m1 = load_m1(); H = Harness(m1); S = build(m1)
B = []
for seed in range(5):
    days, bask, eqm, levm = run_grid(H, S['MR'], 2.0, 50, 0.3, 0.0, tmax=0, seed=seed)
    B.append(bask.assign(seed=seed, test=bask.start >= SPLIT))
B = pd.concat(B)
n_b = len(B) / 5
print(f'baskets per seed: {n_b:.0f} (TRAIN {(~B.test).sum() / 5:.0f}, TEST {B.test.sum() / 5:.0f}); failures (closed at session end '
      f'or below 0): {(B.pnl <= 0).sum() / 5:.1f} per seed')
for k in (5, 10, 15, 20, 25, 30):
    print(f'  P(basket needs >= {k:2d} positions) = {(B.levels >= k).mean():.5f}  (~1 in {1 / max((B.levels >= k).mean(), 1e-9):,.0f});'
          f'  adverse excursion >= ${2 * (k - 1):.0f}')
print('  deepest baskets (seed 0):'); print(B[B.seed == 0].sort_values('levels', ascending=False).head(6)[['start', 'levels', 'bars', 'mae', 'pnl']].round(1).to_string(index=False))
# break-even failure rate: a failure = 50 positions caught in a run of $D that does not retrace before 22:58
for D in (100, 125, 150):
    n = 50; loss = n * D - 2.0 * n * (n - 1) / 2 + 0.21 * n
    pstar = 0.30 / (loss + 0.30)
    per_day = n_b / 76
    print(f'  failure at a ${D} run loses ${loss:,.0f}: break-even failure rate {pstar:.6f} per basket = 1 in {1 / pstar:,.0f} baskets '
          f'= one failure per {1 / pstar / per_day:,.0f} trading days at {per_day:.0f} baskets/day')
nb = n_b
print(f'  observed 0 failures in {nb:,.0f} baskets: 95% upper bound on the failure rate (rule of three) {3 / nb:.5f} = 1 in {nb / 3:,.0f} '
      f'-> the data cannot exclude a failure every {nb / 3 / (n_b / 76):.0f} trading days')
