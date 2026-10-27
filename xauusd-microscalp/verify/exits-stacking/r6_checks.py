"""Step 2 look-ahead / session checks + break-even arithmetic."""
from common import *

m1, H, g = load_m1_harness()
SPLIT = mlib.SPLIT
mr = mr_signal(m1)

# (a) causality of the signal: recompute on data truncated right after bar i for random i -> must be identical
rng = np.random.default_rng(1)
bad = 0
for i in rng.choice(np.arange(300, len(m1) - 10), 300, replace=False):
    s = mr_signal(m1.iloc[:i + 1])
    bad += int(s[-1] != mr[i])
print('signal truncation test: mismatches', bad, 'of 300')
# (b) perturb the future: scramble all bars after bar k; signals up to k unchanged and baskets started before k unaffected until k
k = int(np.searchsorted(m1.index, pd.Timestamp('2026-09-15')))
m2 = m1.copy(); m2.iloc[k + 1:, :4] = m2.iloc[k + 1:, :4].values[::-1]
print('signals before cut identical after scrambling the future:', bool(np.array_equal(mr_signal(m2)[:k + 1], mr[:k + 1])))
d0, b0, _, _ = g.run(mr, seed=0)
g2 = G(m2); d2, b2, _, _ = g2.run(mr_signal(m2), seed=0)
cut = m1.index[k]
e0 = b0[b0.end < cut]; e2 = b2[b2.end < cut]
print('baskets closed before cut identical:', len(e0) == len(e2) and np.allclose(e0.pnl.values, e2.pnl.values))
# (c) session handling: every basket starts and ends on the same date, none spans a session break; end times
print('baskets spanning a date change:', int((b0.end.dt.normalize() != b0.start.dt.normalize()).sum()),
      '| latest basket end time-of-day:', b0.end.dt.strftime('%H:%M').max(), '| latest start:', b0.start.dt.strftime('%H:%M').max(),
      '| earliest start:', b0.start.dt.strftime('%H:%M').min(), '| forced closes:', int((b0.why == 2).sum()))
# (d) profit is ~ 0.30 x baskets: the target, not the direction, makes the money
for per, sel in (('TRAIN', b0.start < SPLIT), ('TEST', b0.start >= SPLIT)):
    b = b0[sel]
    print(f'{per}: baskets {len(b)}, sum pnl {b.pnl.sum():+.1f}, 0.30 x baskets {0.3 * len(b):.1f}')
# (e) break-even: one 50-level failure (as on 2026-08-05 under +$0.05 spread) costs ~$4,272; profit/day ~ $9.4
print(f'one -$4,272 failure = {4272 / 9.42:.0f} TEST-days of profit; break-even failure rate = 1 per {4272 / 0.3:,.0f} baskets '
      f'(~{4272 / 0.3 / 31.3:.0f} trading days at 31.3 baskets/day)')
nb = int((b0.start >= SPLIT).sum())
print(f'TEST has {nb} baskets with 0 failures: 95% upper bound on failure rate 3/{nb} = 1 per {nb / 3:.0f} baskets '
      f'-> cannot exclude a failure every {nb / 3 / 31.3:.0f} trading days, i.e. far more often than break-even allows')
# (f) spread fill uses the hour median from the whole file for zero-spread bars (tiny leak, only late Jun-early Jul):
print('zero-spread bars replaced in TEST:', int(((m1.spread <= 0) & (m1.index >= SPLIT)).sum()))
