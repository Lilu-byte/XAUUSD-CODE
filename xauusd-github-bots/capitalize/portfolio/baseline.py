"""Sanity: reproduce the REPORT numbers for the three candidates and the pair; check the GoldAllAgree proxy."""
from common import *

d = load('H1')
for nm in ['maxi', 'donchian', 'maker_tung']:
    dd, sig, kw = candidate(nm)
    t = simulate(dd, sig, **kw)
    s = stats(t, dd, nm)
    print(nm, 'full', s['per_day'], 'trades', s['trades'], 'win', s['win'], 'dd', s['max_dd'],
          '| train', round(per_day(t, dd, *TRAIN), 2), 'test', round(per_day(t, dd, *TEST), 2),
          'common', round(per_day(t[t.entry_time >= COMMON], dd, COMMON, TEST[1]), 2))
    print('   by year', by_year(t, dd))
    tl = t[t.dir == 1]
    print('   long only (same trades, shorts dropped): train', round(per_day(tl, dd, *TRAIN), 2), 'test', round(per_day(tl, dd, *TEST), 2))

pg, pa = pair_daily(); p = pg + pa
print('pair: days', len(p), 'GAA', round(pg.mean(), 2), 'Asia', round(pa.mean(), 2), 'pair', round(p.mean(), 2),
      'maxdd', round(maxdd(p)), 'losing months', losing_months(p)[:2])
# H1 trading days in common window vs M5 days
h1days = pd.DatetimeIndex(np.unique(d.index.normalize())); h1c = h1days[h1days >= COMMON]
print('H1 days in common', len(h1c), 'M5 days', len(m5_days()), 'diff', set(h1c) ^ set(m5_days()))

# proxy accuracy on the common window
act = gaa_actual_on(d); prx = gaa_proxy(d)
m = ~np.isnan(act)
print('GAA actual long share (H1 closes, common):', round(np.nanmean(act[m]), 3), 'proxy long share:', round(prx[m].mean(), 3),
      'agree', round((act[m] == prx[m]).mean(), 3), 'P(actual|proxy)', round(act[m][prx[m] == 1].mean(), 3),
      'P(proxy|actual)', round(prx[m][act[m] == 1].mean(), 3))
print('proxy long share by year:', pd.Series(prx, index=d.index).groupby(d.index.year).mean().round(2).to_dict())

hg, ht = hold_gold(d, *TEST); print('hold gold test $/day', round(hg, 2), ht[['entry_time', 'exit_time', 'entry', 'exit', 'gross', 'swap', 'pnl']].to_dict('records'))
hg2, _ = hold_gold(d, *TRAIN); print('hold gold train $/day', round(hg2, 2))
hg3, ht3 = hold_gold(d, COMMON, TEST[1]); print('hold gold common $/day', round(hg3, 2), ht3[['gross', 'swap']].to_dict('records'))
