"""Hindsight diagnostic only (NOT a selection step; run after evaluate.py): all 180 grid versions
on the pair window and m15_test, to see (1) whether gating by "pair idle" helps out of sample on
average and (2) whether any version would have met pass tests (a) and (b) even with hindsight.
Writes ../grid_all_windows.csv. Run: python3 -I diag.py
"""
import sys; sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/idle-time/code')
import json, itertools, numpy as np, pandas as pd
import idle as I, harness as H
from grid import SIGNALS, TPS, SLS, GATES, Base, alone, label, OUT

G = pd.read_csv(OUT + 'grid_m15_train.csv')
bases = {w: Base(w) for w in ('pair', 'm15_test')}
rows = []
for (fam, spec), tp, sl, gate in itertools.product(SIGNALS, TPS, SLS, GATES):
    r = dict(family=fam, signal=label(spec), tp=tp, sl=sl, gate=gate)
    for w, b in bases.items():
        t = I.stream(w, spec, tp, sl, gate); a = alone(t, w); c = b.score(t)
        r.update({f'{w}_alone_per_day': a['per_day'], f'{w}_alone_trades_day': a['trades_day'],
                  f'{w}_comb_per_day': c['per_day'], f'{w}_comb_trades_day': c['trades_day'],
                  f'{w}_comb_max_dd': c['max_dd'], f'{w}_comb_max_dd_mtm': c['max_dd_mtm']})
    rows.append(r)
D = pd.DataFrame(rows)
D = D.merge(G[['signal', 'tp', 'sl', 'gate', 'alone_per_day']].rename(columns={'alone_per_day': 'train_alone_per_day'}),
            on=['signal', 'tp', 'sl', 'gate'])
D.to_csv(OUT + 'grid_all_windows.csv', index=False)

print('mean stream $/day by gate (train / m15_test / pair):')
for g in GATES:
    s = D[D.gate == g]
    print(f'  {g:6s}: {s.train_alone_per_day.mean():+.2f} / {s.m15_test_alone_per_day.mean():+.2f} / {s.pair_alone_per_day.mean():+.2f}'
          f'   positive on pair {int((s.pair_alone_per_day > 0).sum())}/{len(s)}, on m15_test {int((s.m15_test_alone_per_day > 0).sum())}/{len(s)}')
# same signal/TP/SL: gated minus ungated
k = ['signal', 'tp', 'sl']
u = D[D.gate == 'none'].set_index(k)
for g in ('entry', 'strict'):
    s = D[D.gate == g].set_index(k)
    for w in ('train', 'm15_test', 'pair'):
        diff = s[f'{w}_alone_per_day'] - u[f'{w}_alone_per_day']
        print(f'  {g} minus ungated, {w}: mean {diff.mean():+.2f}/day, gated better in {int((diff > 0).sum())}/{len(diff)}')
a = (D.pair_comb_per_day >= 4.66) & (D.pair_comb_trades_day >= 1.89) & (D.pair_comb_max_dd >= -294) & (D.pair_comb_max_dd_mtm >= -255)
b = (D.m15_test_comb_per_day >= 4.06) & (D.m15_test_comb_max_dd >= -308) & (D.m15_test_comb_max_dd_mtm >= -417)
print(f'hindsight: meet (a) {int(a.sum())}/{len(D)}, meet (b) {int(b.sum())}/{len(D)}, both {int((a & b).sum())}')
a2 = (D.pair_comb_per_day >= 4.66) & (D.pair_comb_trades_day >= 1.89)
print(f'  pair window: $/day and +0.3 trades/day met by {int(a2.sum())}; of those, best max_dd '
      f'{D[a2].pair_comb_max_dd.max():.0f} and best max_dd_mtm {D[a2].pair_comb_max_dd_mtm.max():.0f} (limits -294 / -255)')
print('  train-vs-test rank correlation of stream $/day: m15_test %.2f, pair %.2f' % (
    D.train_alone_per_day.corr(D.m15_test_alone_per_day, method='spearman'),
    D.train_alone_per_day.corr(D.pair_alone_per_day, method='spearman')))
pos3 = (D.train_alone_per_day > 0) & (D.m15_test_alone_per_day > 0) & (D.pair_alone_per_day > 0)
print(f'  positive on train, m15_test and pair: {int(pos3.sum())}')
if pos3.any():
    print(D[pos3][['signal', 'tp', 'sl', 'gate', 'train_alone_per_day', 'm15_test_alone_per_day', 'pair_alone_per_day',
                   'pair_comb_max_dd', 'pair_comb_max_dd_mtm', 'm15_test_comb_max_dd']].to_string())
