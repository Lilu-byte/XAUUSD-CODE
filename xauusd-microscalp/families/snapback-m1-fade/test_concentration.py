"""Breakdown of the TEST result (no new configurations): how concentrated the TEST profit is, and a day-bootstrap
interval for the TEST per-day mean."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from evalx import *
from picks import PICKS
m, H = load_all(); f = feats(m)
rng = np.random.default_rng(0)
for name, p in PICKS.items():
    d, t = runp(H, f, p)
    x = d[d.index >= SPLIT].pnl.sort_values(ascending=False)
    bs = [rng.choice(x.values, len(x)).mean() for _ in range(5000)]
    tr = d[d.index < SPLIT].pnl; bst = [rng.choice(tr.values, len(tr)).mean() for _ in range(5000)]
    print(f'{name}: TEST total {x.sum():+.1f} over {len(x)} days; best 3 days {x.iloc[:3].round(1).tolist()} = {x.iloc[:3].sum():+.1f}; '
          f'TEST/day without best day {x.iloc[1:].mean():+.2f}, without best 3 {x.iloc[3:].mean():+.2f}; '
          f'day-bootstrap 90% CI TEST [{np.percentile(bs, 5):+.2f}, {np.percentile(bs, 95):+.2f}], TRAIN [{np.percentile(bst, 5):+.2f}, {np.percentile(bst, 95):+.2f}]')
