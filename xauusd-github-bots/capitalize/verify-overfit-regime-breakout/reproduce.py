"""Step 1: reproduce the candidate's headline numbers with my own signal code, plus hold baselines and t-stats."""
import numpy as np, pandas as pd
from vcommon import *

d = load('H1'); t = run(d, **PICK); p = daily(t, d)
for nm, (a, b) in [('TRAIN', TRAIN), ('TEST', TEST), ('COMMON', COMMON)]:
    x = win(p, a, b); tt = t[(t.exit_time >= a) & (t.exit_time <= pd.Timestamp(b) + pd.Timedelta(days=1))]
    s = summ(x); tstat = x.mean() / (x.std() / np.sqrt(len(x)))
    print(nm, s, 'trades', len(tt), 'win%', round((tt.pnl > 0).mean() * 100, 1), 't-stat', round(tstat, 2),
          '| long', round(tt[tt.dir > 0].pnl.sum()), f'({(tt.dir > 0).sum()})', 'short', round(tt[tt.dir < 0].pnl.sum()), f'({(tt.dir < 0).sum()})')
print('by year', p.groupby(p.index.year).mean().round(2).to_dict())
h = hold_daily(d)
for nm, (a, b) in [('TRAIN', TRAIN), ('TEST', TEST), ('COMMON', COMMON)]:
    hx = win(h, a, b).reindex(win(p, a, b).index, fill_value=0.0)
    print('HOLD', nm, summ(hx))
x = win(p, *TEST); hx = win(h, *TEST).reindex(x.index, fill_value=0)
print('test excluding 2025: strategy', round(x[x.index.year != 2025].mean(), 2), 'hold', round(hx[hx.index.year != 2025].mean(), 2))
print('test by year hold', hx.groupby(hx.index.year).mean().round(2).to_dict())
# common window with pair
days, pp, A, B = pair_daily(); mine = p.reindex(days, fill_value=0.0)
for lab, z in [('pair', pp), ('pick alone', mine), ('pair+pick', pp + mine)]:
    print('COMMON', lab, summ(z))
print('corr daily', round(np.corrcoef(pp, mine)[0, 1], 2), 'weekly', round(pp.resample('W').sum().corr(mine.resample('W').sum()), 2))
hc = h.reindex(days, fill_value=0.0)
print('COMMON pair+hold0.01', summ(pp + hc), '| hold alone', summ(hc))
t.to_csv('/tmp/claude-0/oanda-verify-overfit-rb/pick_trades_mt5.csv', index=False)
