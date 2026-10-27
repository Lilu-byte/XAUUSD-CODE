"""TRAIN-only bracket grid for two candidates that were positive in both TRAIN halves in scan5."""
import sys, itertools; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from library import *
H = Harness(); m = H.m1; f = build(m); L = library(m, f)
C = {'fade_r1>3a|vw': -L['r1>3a|vw'], 'fade_z10>2.5': -L['z10>2.5']}
TP = (0.1, 0.2, 0.3, 0.5, 0.7, 1.0); SL = (0.5, 1, 2, 3, 5, 8); TO = (3, 5, 10, 20, 30)
Am = H.dates < A_SPLIT; Tm = H.dates < SPLIT; rows = []
for name, sig in C.items():
    for tp, sl, to in itertools.product(TP, SL, TO):
        days, trades = H.run(sig, tp, sl, to, 1)
        rows.append(dict(sig=name, tp=tp, sl=sl, to=to, perA=days.pnl[Am].mean(), perB=days.pnl[Tm & ~Am].mean(),
                         **summarize(days, trades, 'train')))
r = pd.DataFrame(rows); r.to_csv('bracket2_train.csv', index=False)
pd.set_option('display.width', 250)
for name in C:
    x = r[r.sig == name]
    print(name, ' configs', len(x), ' positive', (x.per_day > 0).sum(), ' positive both halves', ((x.perA > 0) & (x.perB > 0)).sum())
    print(x.sort_values('per_day', ascending=False)[['tp', 'sl', 'to', 'per_day', 'perA', 'perB', 'trades_day', 'win', 'per_trade', 'worst_day', 'max_dd']].head(8).round(3).to_string(index=False))
    for to in (5, 10):
        print(' timeout', to); print(x[x.to == to].pivot(index='sl', columns='tp', values='per_day').round(2).to_string())
