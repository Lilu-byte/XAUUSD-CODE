"""Diagnostics for the frozen pick: per-year long/short split, no-look-ahead spot check of the D1 gate, D1 weekday mix."""
import numpy as np, pandas as pd
from common import *
R = d1_regimes(); d, s0, kw = base('DON'); g = np.nan_to_num(htf(d, 'D1', R['MOM6'].values))
t = pd.read_csv('final_trades.csv', parse_dates=['entry_time', 'exit_time'])
print(t.pivot_table(index=t.exit_time.dt.year, columns='dir', values='pnl', aggfunc=['count', 'sum']).round(0))
D = load('D1'); print('D1 weekday counts', D.index.dayofweek.value_counts().sort_index().to_dict())
# spot check: gate on each H1 bar must equal the regime of the LAST D1 bar with date < H1 bar's date
rng = np.random.default_rng(0); bad = 0
for i in rng.choice(np.arange(5000, len(d)), 3000, replace=False):
    ts = d.index[i]; prev = R['MOM6'][R.index < ts.normalize()]
    if prev.iloc[-1] != g[i]: bad += 1
print('look-ahead spot check mismatches:', bad, 'of 3000')
# current state
print('last D1', D.index[-1].date(), 'close', D.close.iloc[-1], 'close 126 bars ago', D.close.iloc[-127], '-> MOM6', R.MOM6.iloc[-1])
print('open trade at end?', t.exit_time.max(), 'last entry', t.entry_time.max(), t.tail(3)[['entry_time','dir','entry','exit_time','exit','pnl','why']])
