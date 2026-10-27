"""Diagnostic on m15_train only, run after the picks were fixed (it cannot change them):
how stable is the change pick (re-entry on M15 EMA5/20 while H1+H4 stay up) to its fast EMA and
anchor choice? Usage: python3 -I neighbours.py -> ../train_neighbours.csv + printed table."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/allagree-more/code')
import pandas as pd
import aa_more as A, specs as SP
from train_grid import evaluate
H = A.H
W = 'm15_train'

if __name__ == '__main__':
    pd.set_option('display.width', 220)
    base = H.pair_parts(W)
    bfix = {'AllAgree': A.baseline_aa(W, 'fixed'), 'AsiaBreak': base['AsiaBreak']}
    rows = []
    for anchors in (('H1', 'H4'), ('M30', 'H1', 'H4')):
        for fe in ((3, 12), (4, 16), (5, 15), (5, 20), (5, 25), (6, 24), (8, 32)):
            spec = dict(kind='change/armed', anchors=anchors, fast=('M15',), fast_emas=fe)
            rows.append(evaluate(spec, W, base, bfix))
    T = pd.DataFrame(rows)
    T.to_csv('/mnt/project-files/xauusd-more-trades/allagree-more/train_neighbours.csv', index=False)
    print(T[['name', 'per_day', 'per_day_fixed', 'trades_day', 'max_dd', 'max_dd_mtm', 'own_per_day']].to_string(index=False))
    print('versions scored on m15_train here:', len(T), '(one of them, H1+H4 / 5,20, repeats the pick)')
