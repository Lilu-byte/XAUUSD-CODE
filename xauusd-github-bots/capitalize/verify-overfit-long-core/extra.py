"""Step 5: execution and timing robustness of SMA 50/200 on the test window.
(a) fill at 02:00 server on the H1 data instead of the D1 open; (b) circular shifts of the on/off pattern
inside the test window (same runs, random phase); (c) margin: max open lots with the pair."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-overfit-long-core')
from vsim import *

D1 = gbt.load('D1'); H1 = gbt.load('H1'); c = D1.close
on = golden(c, 50, 200)
p, held, t = mtm(on, D1); ph, _, _ = mtm(np.ones(len(D1), bool), D1)

# (a) 02:00 server fill: first H1 bar at/after 02:00 on each D1 date; fall back to D1 open
h = H1[H1.index.hour >= 2]
f2 = h.groupby(h.index.normalize()).open.first().reindex(D1.index)
fill = np.where(np.isnan(f2.values), D1.open.values, f2.values)
p2, _, t2 = mtm(on, D1, fill=fill)
for lbl, w in (('train B', TRAIN_B), ('test', TEST)):
    print(f'02:00 fill {lbl}: $/day {win(p2, w).mean():.2f} (D1-open fill {win(p, w).mean():.2f}, hold {win(ph, w).mean():.2f})')

# (b) circular phase shifts of the rule's own on/off pattern inside the test window
idx = np.flatnonzero((D1.index >= TEST[0]) & (D1.index <= TEST[1])); i0, i1 = idx[0], idx[-1] + 1
seg = on[i0:i1]; res = []
for k in range(0, len(seg), 5):
    x = on.copy(); x[i0:i1] = np.roll(seg, k)
    q, _, _ = mtm(x, D1); res.append(win(q, TEST).mean())
res = np.array(res); base = win(p, TEST).mean()
print(f'phase-shifted copies of the same on/off pattern ({len(res)}): median ${np.median(res):.2f}/day, '
      f'5-95% {np.percentile(res, 5):.2f}..{np.percentile(res, 95):.2f}; the rule beats {np.mean(res < base) * 100:.0f}% of them')

# (c) margin / lots
pp, a, b, days = pair_daily()
ev = sorted([(x, 1) for x in a.entry_time] + [(x, -1) for x in a.exit_time] + [(x, 1) for x in b.entry_time] + [(x, -1) for x in b.exit_time],
            key=lambda z: (z[0], z[1]))
cur = mx = 0
for _, dd in ev:
    cur += dd; mx = max(mx, cur)
print('pair max simultaneous 0.01-lot positions:', mx, '-> with the core: max', mx + 1, 'x 0.01 lot')
px = 4195.2
for lev in (20, 100):
    print(f'  1:{lev}: 0.03 lot margin ${3 * px / lev:.0f}; a 5% drop on 0.03 lot costs ${0.05 * px * 3:.0f}; '
          f'margin level after it from $3,000: {(3000 - 0.05 * px * 3) / (3 * px * 0.95 / lev) * 100:.0f}%')
