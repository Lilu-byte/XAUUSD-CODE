# Superseded by asia_ea.py, which copies GoldAsiaBreak v1.10 line by line; kept for the record.
import numpy as np, pandas as pd
from engine import prep, sim
e = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
days = pd.bdate_range('2025-05-06', '2026-10-09')
ea = e.groupby(e.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0)
P = prep('M5'); P['sc'] = np.ones_like(P['sc'])   # the EA uses fixed $ TP/SL, not price-scaled
for tp, sl in ((5, 30), (5, 50), (8, 50)):
    ab = sim(P, 'asia_break', 'any', 540, tp, sl).pnl.reindex(days, fill_value=0)
    for name, s in (('EA', ea), ('Asia', ab), ('EA+Asia', ea + ab)):
        eq = s.cumsum(); m = s.groupby(s.index.to_period('M')).sum()
        print(tp, sl, name, 'per_day', round(s.mean(), 2), 'days>=5', round((s >= 4.99).mean(), 2), 'max_dd', round((eq - eq.cummax()).min(), 0),
              'worst_month', round(m.min(), 0), 'pos_months', round((m > 0).mean(), 2), 'total', round(s.sum(), 0))
    print('  corr EA/Asia daily', round(ea.corr(ab), 2))
