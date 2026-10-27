"""Paired effects from stageB2_train.csv (TRAIN only): what changes when only max_open / cooldown / gate changes."""
import pandas as pd, numpy as np
R = pd.read_csv('/mnt/project-files/xauusd-microscalp/families/exits-stacking/stageB2_train.csv')
R = R[R.be_trig == 0]
R['dense'] = ~R.sig.isin(['MR', 'MR6'])
key = ['sig', 'tp', 'sl', 'timeout', 'gate', 'lag', 'cooldown']
b = R[R.max_open == 1].set_index(key)
for mo in (3, 5, 10, 50):
    x = R[R.max_open == mo].set_index(key).join(b, rsuffix='_1', how='inner')
    for dn, g in x.groupby('dense'):
        print(f'max_open {mo:2d} vs 1 ({"dense" if dn else "MR/MR6"} signals, n={len(g)}): trades x{(g.trades_day / g.trades_day_1).median():.2f}, '
              f'per_trade change median {(g.per_trade - g.per_trade_1).median():+.3f}, per_day change median {(g.per_day - g.per_day_1).median():+.2f}, '
              f'worst_day change median {(g.worst_day - g.worst_day_1).median():+.1f}')
key2 = ['sig', 'tp', 'sl', 'timeout', 'gate', 'lag', 'max_open']
b = R[R.cooldown == 0].set_index(key2)
for cd in (1, 3, 5, 10):
    x = R[R.cooldown == cd].set_index(key2).join(b, rsuffix='_0', how='inner')
    for dn, g in x.groupby('dense'):
        print(f'cooldown {cd:2d} vs 0 ({"dense" if dn else "MR/MR6"}, n={len(g)}): trades x{(g.trades_day / g.trades_day_0).median():.2f}, '
              f'per_trade change {(g.per_trade - g.per_trade_0).median():+.3f}, resid change {(g.resid - g.resid_0).median():+.3f}')
key3 = ['sig', 'tp', 'sl', 'timeout', 'max_open', 'cooldown']
b = R[R.gate == 0].set_index(key3)
for gt, lag in ((0.10, 0), (0.15, 0), (0.20, 0), (0.10, 1)):
    x = R[(R.gate == gt) & (R.lag == lag)].set_index(key3).join(b, rsuffix='_n', how='inner')
    for dn, g in x.groupby('dense'):
        print(f'gate {gt} lag {lag} vs none ({"dense" if dn else "MR/MR6"}): trades x{(g.trades_day / g.trades_day_n).median():.2f}, spread paid {g.avg_spr.median():.3f} vs {g.avg_spr_n.median():.3f}, '
              f'per_trade change {(g.per_trade - g.per_trade_n).median():+.3f}, resid change {(g.resid - g.resid_n).median():+.3f}')
