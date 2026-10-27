"""Stage 3: score the frozen pick ONCE out of sample. Nothing here feeds back into the choice.
Pick (from grid_train.py + stage2_train.py, train 2016-07..2021-12 only):
  DON both directions, gated by D1 6-month momentum (MOM6), channel exit only."""
import sys, numpy as np, pandas as pd
from common import *
pd.set_option('display.width', 220)
R = d1_regimes(); d, sig0, kw = base('DON'); sig = gate(d, sig0, 'MOM6', False, R)
t = simulate(d, sig, **kw)
P_ = daily(t, d)

def block(a, b, label):
    p = window_daily(t, d, a, b); tt = trades_in(t, a, b); s = summarize(p, tt)
    s['trades_yr'] = round(len(tt) / (len(p) / 260), 1); print(label, s); return p, tt, s

ptr, ttr, s_tr = block(*TRAIN, 'TRAIN')
pte, tte, s_te = block(*TEST, 'TEST ')
print('by year $/day:', years(P_).to_dict())
print('test long/short split:', tte.groupby('dir').pnl.agg(['count', 'sum', 'mean']).round(1).to_dict())

# coin flip: same entry bars, same exits, random direction; scored on the test window
rng = np.random.default_rng(1); nz = sig != 0; cf_te = []; cf_tr = []
for _ in range(100):
    r = sig.copy(); r[nz] = np.where(rng.random(nz.sum()) < .5, 1.0, -1.0)
    tr_ = simulate(d, r, **kw)
    cf_te.append(window_daily(tr_, d, *TEST).mean()); cf_tr.append(window_daily(tr_, d, *TRAIN).mean())
cf_te, cf_tr = np.array(cf_te), np.array(cf_tr)
print(f'coin-flip test: median {np.median(cf_te):.2f}/day, pick beats {np.mean(cf_te < s_te["per_day"])*100:.0f}% | '
      f'train: median {np.median(cf_tr):.2f}, beats {np.mean(cf_tr < s_tr["per_day"])*100:.0f}%')

# baselines
print('hold 0.01 lot (net swap, gross): test', hold_per_day(d, *TEST), 'common', hold_per_day(d, *COMMON))

# common window, alone and with the pair
days, pp, A, B = pair_daily()
mine = P_.reindex(days, fill_value=0.0)
both_ = pp + mine
for lab, x in [('pair', pp), ('regime-breakout alone', mine), ('pair + regime-breakout', both_)]:
    print('COMMON', lab, summarize(x))
print('corr daily with pair', round(np.corrcoef(pp, mine)[0, 1], 2),
      ' corr weekly', round(pp.resample('W').sum().corr(mine.resample('W').sum()), 2))
tc = trades_in(t, *COMMON); print('common trades', len(tc), 'win', round((tc.pnl > 0).mean() * 100, 1))
# max simultaneous lots
iv = [(r.entry_time, r.exit_time + pd.Timedelta(hours=1)) for r in tc.itertuples()]
ia = [(r.entry_time, r.exit_time) for r in A.itertuples()]
ib = [(r.entry_time, r.exit_time) for r in B.itertuples()]
print('max open: pair', max_open(ia + ib), ' pair+mine', max_open(ia + ib + iv), ' mine alone', max_open(iv))
# trade-list sanity
print('sanity: entries only where regime agreed:',
      bool(((sig[t.ei.astype(int).values - 1] == t.dir.values)).all()),
      '| exit after entry:', bool((t.xi >= t.ei).all()),
      '| worst trade', round(t.pnl.min(), 1), '| longest hold (H1 bars)', int((t.xi - t.ei).max()),
      '| swap total', round(t.swap.sum(), 0))
print(t.groupby('why').pnl.agg(['count', 'mean']).round(2))
s = pd.DataFrame([dict(window='train', **s_tr), dict(window='test', **s_te)])
s.to_csv('final_summary.csv', index=False)
pd.DataFrame({'per_day': years(P_)}).to_csv('final_by_year.csv')
t.drop(columns=['ei', 'xi']).round(2).to_csv('final_trades.csv', index=False)
