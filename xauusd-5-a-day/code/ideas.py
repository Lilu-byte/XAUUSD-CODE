import numpy as np, pandas as pd
from engine import prep, sim, summ
f = lambda d: {k: round(float(v), 2) for k, v in d.items() if k in ('per_day', 'hit5', 'loss_days', 'worst_day', 'max_dd', 'worst_month', 'pos_months', 'trades_day')}
# EA trades from the other thread, by day
e = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
days = pd.bdate_range('2025-05-06', '2026-10-09')
ea = e.groupby(e.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0)
print('EA all-agree, by exit day:', 'per_day', round(ea.mean(), 2), 'days with trade', round((ea != 0).mean(), 2), 'days >=5', round((ea >= 5).mean(), 2),
      'median trade', e.pnl_usd.median(), 'top 10% of trades make', round(e.pnl_usd.nlargest(len(e) // 10).sum(), 0), 'of', round(e.pnl_usd.sum(), 0))
for tf, lo in (('M15', '2022-07-08'), ('M5', '2025-05-06')):
    P = prep(tf); S = P['sigs']; ab = S['asia_break']
    S['ab+H4'] = np.where(ab == S['H4'], ab, 0); S['ab+D1'] = np.where(ab == S['D1'], ab, 0)
    S['ab+H4H1'] = np.where(ab == S['H4+H1'], ab, 0)
    print('==', tf)
    for sig in ('asia_break', 'ab+H4', 'ab+D1', 'ab+H4H1'):
        for tp, sl in ((5, 30), (5, 50), (8, 50)):
            r = sim(P, sig, 'any', 540, tp, sl); r = r[r.index >= lo]
            print(sig, tp, sl, f(summ(r)))
    # 2 tries per day, second try recovers the first loss
    for tp, sl in ((5, 20), (5, 30)):
        r = sim(P, 'asia_break', 'any', 540, tp, sl, max_tr=2, recover=1); print('asia 2 tries recover', tp, sl, f(summ(r[r.index >= lo])))
