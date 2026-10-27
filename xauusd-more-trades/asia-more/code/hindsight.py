"""HINDSIGHT diagnostic only (not a selection step, no candidate is chosen here): score all
127 train-grid versions on the pair window and m15_test, to see whether the negative result is
an artefact of the training pick or holds for every version. Writes ../hindsight.csv.
Usage: python3 -I hindsight.py"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/asia-more/code')
import json
import pandas as pd
import asia_more as A
from train_grid import versions, build, alone_stats
H = A.H
rows = []
for w in ('pair', 'm15_test'):
    base = H.pair_parts(w)
    for fam, spec in versions():
        comb, alone, t = build(spec, w, base)
        s = H.score(comb, w, by_period=False)
        a = alone_stats(alone, w)
        rows.append(dict(window=w, family=fam, spec=json.dumps(spec), per_day=s['per_day'], trades_day=s['trades_day'],
                         max_dd=s['max_dd'], max_dd_mtm=s['max_dd_mtm'], alone_per_day=a['per_day']))
R = pd.DataFrame(rows)
R.to_csv('/mnt/project-files/xauusd-more-trades/asia-more/hindsight.csv', index=False)
p = R[R.window == 'pair'].set_index('spec'); t = R[R.window == 'm15_test'].set_index('spec')
pa = (p.per_day >= 4.66) & (p.trades_day >= 1.89) & (p.max_dd >= -294) & (p.max_dd_mtm >= -255)
tb = (t.per_day >= 4.06) & (t.max_dd >= -308) & (t.max_dd_mtm >= -417)
print('versions meeting (a) on the pair window:', int(pa.sum()), '| meeting (b) on m15_test:', int(tb.sum()),
      '| both:', int((pa & tb).sum()))
print('pair window, versions with combined per_day >= 4.66 and +0.3 trades:', int(((p.per_day >= 4.66) & (p.trades_day >= 1.89)).sum()),
      '; of those, best max_dd', p[(p.per_day >= 4.66) & (p.trades_day >= 1.89)].max_dd.max())
print('pair window, versions with max_dd >= -294 and mtm >= -255 and +0.3 trades:',
      int(((p.max_dd >= -294) & (p.max_dd_mtm >= -255) & (p.trades_day >= 1.89)).sum()),
      '; their best per_day', p[(p.max_dd >= -294) & (p.max_dd_mtm >= -255) & (p.trades_day >= 1.89)].per_day.max())
for fam in p.family.unique():
    g = p[p.family == fam]; gt = t[t.family == fam]
    print(f'  {fam:4s} pair: extra $/day {g.alone_per_day.min():+.2f} .. {g.alone_per_day.max():+.2f} (>0 in {(g.alone_per_day > 0).sum()}/{len(g)}), '
          f'combined max_dd {g.max_dd.min():.0f} .. {g.max_dd.max():.0f} | m15_test extra >0 in {(gt.alone_per_day > 0).sum()}/{len(gt)}')
