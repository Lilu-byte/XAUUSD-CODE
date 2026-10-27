"""TRAIN-only diagnostic: why fill-free fade edges vanish under a TP<=$1 bracket. Compares a pure time exit
(TP/SL far away) with capped brackets, and shows how much of the 5-min edge comes from moves larger than $1."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from library import *
H = Harness(); m = H.m1; f = build(m); L = library(m, f)
F5 = fwd(m, (5,))[5]; tr = m.index < SPLIT
for name in ('r3>6$', 'rexp>3', 'r3>3a|avw', 'r1>3a|vw'):
    sig = -L[name]
    x = (F5 * sig)[(sig != 0) & tr]; x = x[~np.isnan(x)]
    print(f'{name} fade: n/day {len(x)/47:.1f}  mean 5m move {x.mean():+.3f}; contribution of |move|>$1: {x[np.abs(x) > 1].sum()/len(x):+.3f}, '
          f'of |move|<=$1: {x[np.abs(x) <= 1].sum()/len(x):+.3f};  mean of move clipped to [-8,+1]: {np.clip(x, -8, 1).mean():+.3f}')
    for tp, sl in ((50, 50), (1.0, 8), (1.0, 3), (0.5, 3), (0.2, 3)):
        d, t = H.run(sig, tp, sl, 5, 1); s = summarize(d, t, 'train')
        print(f'     TP {tp:>4} SL {sl:>2} timeout 5: per_trade {s["per_trade"]:+.3f}  per_day {s["per_day"]:+.2f}  trades/day {s["trades_day"]:.1f}')
