"""Diagnostic only, run after the picks were scored (it chooses nothing): the same versions as
train_grid.py on pair, m15_test and h1_old. Do train results carry over? Would any version have met
the pass lines (a) and (b) with hindsight? How does the short side do on 2016-22?
Usage: python3 -I hindsight.py  -> ../hindsight.csv + printed summary."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/allagree-more/code')
import json
import numpy as np, pandas as pd
import aa_more as A, specs as SP
from train_grid import evaluate
H = A.H
D = '/mnt/project-files/xauusd-more-trades/allagree-more/'
K = ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm', 'own_per_day', 'alone_per_day', 'per_day_fixed')

def run_window(w):
    T = pd.read_csv(D + 'train_grid.csv')
    base = H.pair_parts(w)
    bfix = {'AllAgree': A.baseline_aa(w, 'fixed'), 'AsiaBreak': base['AsiaBreak']}
    R = pd.DataFrame([evaluate(json.loads(s), w, base, bfix) for s in T.spec])
    print('done', w, flush=True)
    return w, R


if __name__ == '__main__':
    import multiprocessing as mp
    pd.set_option('display.width', 250)
    T = pd.read_csv(D + 'train_grid.csv')
    out = T[['name', 'family', 'kind', 'spec'] + [k for k in K]].rename(columns={k: 'train_' + k for k in K})
    with mp.get_context('fork').Pool(3) as pool:     # one process per window
        res = dict(pool.map(run_window, ('pair', 'm15_test', 'h1_old')))
    for w, R in res.items():
        for k in K: out[w + '_' + k] = R[k].values if k in R else np.nan
    out.to_csv(D + 'hindsight.csv', index=False)
    a = (out.pair_per_day >= 4.66) & (out.pair_trades_day >= 1.89) & (out.pair_max_dd >= -294) & (out.pair_max_dd_mtm >= -255)
    b = (out.m15_test_per_day >= 4.06) & (out.m15_test_max_dd >= -308) & (out.m15_test_max_dd_mtm >= -417)
    print('\nversions', len(out), '| meet (a) on pair:', int(a.sum()), '| meet (b) on m15_test:', int(b.sum()), '| both:', int((a & b).sum()))
    for fam in ('change', 'short', 'sibling'):
        F = out[out.family == fam]
        print(f'\n{fam}: {len(F)} versions; own $/day > 0 on train {int((F.train_own_per_day > 0).sum())}, '
              f'm15_test {int((F.m15_test_own_per_day > 0).sum())}, pair {int((F.pair_own_per_day > 0).sum())}, '
              f'h1_old {int((F.h1_old_own_per_day > 0).sum())}; train & test & pair {int(((F.train_own_per_day > 0) & (F.m15_test_own_per_day > 0) & (F.pair_own_per_day > 0)).sum())}')
        print('  rank corr of own $/day, train vs m15_test %.2f, train vs pair %.2f, train vs h1_old %.2f' % (
            F.train_own_per_day.corr(F.m15_test_own_per_day, method='spearman'),
            F.train_own_per_day.corr(F.pair_own_per_day, method='spearman'),
            F.train_own_per_day.corr(F.h1_old_own_per_day, method='spearman')))
        print('  meet (a):', int(a[F.index].sum()), ' meet (b):', int(b[F.index].sum()), ' both:', int((a & b)[F.index].sum()))
    cols = ['name', 'train_own_per_day', 'pair_per_day', 'pair_trades_day', 'pair_max_dd', 'pair_max_dd_mtm',
            'm15_test_per_day', 'm15_test_max_dd', 'm15_test_max_dd_mtm', 'h1_old_own_per_day']
    print('\nversions meeting (a):'); print(out[a][cols].to_string(index=False))
    print('\nversions meeting (b):'); print(out[b][cols].to_string(index=False))
    S = out[out.family == 'short']
    print('\nshort side, own $/day by window (median / best / share > 0):')
    for w in ('train', 'm15_test', 'pair', 'h1_old'):
        x = S[w + '_own_per_day']; print(f'  {w:9s} median {x.median():+.2f}  best {x.max():+.2f}  >0 {(x > 0).mean():.0%}')
