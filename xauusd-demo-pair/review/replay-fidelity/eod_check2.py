import sys; sys.dont_write_bytecode = True
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-demo-pair/review/replay-fidelity')
from asia_port import ea_trades, per_day, days
csv = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
ea = csv.groupby(csv.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0)
for tp in (5, 8):
    for name, ct in (('as written 23:30', 1410), ('uniform 22:45', 1365)):
        A = per_day(ea_trades(tp, 50, close_tod=ct)); s = ea + A; eq = s.cumsum()
        print(f'TP{tp} {name}: Asia {A.mean():.2f}/day, EA+Asia {s.mean():.2f}/day, days>=5 {(s>=4.99).mean():.2f}, max_dd {(eq-eq.cummax()).min():.0f}, worst month {s.groupby(s.index.to_period("M")).sum().min():.0f}')
