"""Scores the PDH break replay the project's way (18 Oct 2026). Prints; results also saved to results.txt by the caller."""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
import pdh as P
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/code'); import harness as H

def zero_cost(tf):
    s = (P.SPREAD, P.SLIP, P.SWAP_L); P.SPREAD = P.SLIP = P.SWAP_L = 0.0
    r = P.run(tf); P.SPREAD, P.SLIP, P.SWAP_L = s; return r

for tf in ('M15', 'H1'):
    z = zero_cost(tf); print(tf, 'no costs: trades', len(z), 'R/trade %.3f' % z.R.mean(), '$ %.0f' % z.pnl.sum())

m15 = P.run('M15'); h1 = P.run('H1'); m15ea = P.run('M15', lots='ea'); h1ea = P.run('H1', lots='ea')
for name, r in (('M15 0.01', m15), ('H1 0.01', h1), ('M15 EA sizing', m15ea), ('H1 EA sizing', h1ea)):
    y = r.groupby(r.exit_time.dt.year).agg(n=('pnl', 'size'), usd=('pnl', 'sum'), R=('R', 'mean')).round(2)
    print('\n', name, 'by year\n', y.T.to_string())
print('\nM15 EA sizing lots used:', m15ea.lots.value_counts().sort_index().to_dict())
print('H1 EA sizing lots used:', h1ea.lots.value_counts().sort_index().to_dict())
h1_last = h1.groupby(h1.exit_time.dt.year).atr.median().round(1).to_dict(); print('H1 median ATR by year', h1_last)

for w in ('pair', 'm15_train', 'm15_test', 'h1_old'):
    r = h1 if w == 'h1_old' else m15
    base = H.pair_parts(w)
    print('\n==', w, '(PDH from', 'H1' if w == 'h1_old' else 'M15', ')')
    print('  PDH alone ', H.score(r, w))
    print('  pair      ', H.score(base, w))
    print('  pair + PDH', H.score({**base, 'PDH': r}, w))
    print('  corr PDH vs pair daily', round(H.per_day(r, w).corr(sum(H.per_day(t, w) for t in base.values())), 2))

# holding gold, 0.01 lot, same windows (buy first close, sell last close, nightly swap)
d1 = P.load('D1')
for w in ('pair', 'm15_train', 'm15_test', 'h1_old'):
    a, b = H.WINDOWS[w][1:]
    x = d1[a:b].close; nd = len(H.days(w)); sw = 0.126 * (x.index[-1] - x.index[0]).days
    print('hold 0.01 lot', w, '$/day %.2f' % ((x.iloc[-1] - x.iloc[0] - 0.4 - sw) / nd),
          'mtm dd %.0f' % (x - x.cummax()).min())
m15.to_csv('../trades_M15.csv', index=False); h1.to_csv('../trades_H1.csv', index=False)
