"""TRAIN-only robustness of the three picks (same battery as the TEST run)."""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from evalx import *
from picks import PICKS
m, H = load_train(); f = feats(m)
res = {}
for name, p in PICKS.items():
    out, d, t = battery(H, f, p, 'train')
    a, b = summ(d, t, 'A'), summ(d, t, 'B')
    print(f'=== {name} TRAIN  (halves: Jun26-Jul31 {a["per_day"]:+.2f}/day, Aug {b["per_day"]:+.2f}/day; exit kinds TP/SL/mixed/time '
          f'{(t.kind == 0).mean():.2f}/{(t.kind == 1).mean():.2f}/{(t.kind == 2).mean():.2f}/{(t.kind == 3).mean():.2f})')
    for k, r in out.items(): print(fmt(k, r))
    res[name] = out
json.dump(res, open(FAM + 's5_train_robust.json', 'w'), indent=1, default=float)
