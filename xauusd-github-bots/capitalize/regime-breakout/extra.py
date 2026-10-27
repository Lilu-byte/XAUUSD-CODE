"""Exposure on the common window (hours with 1/2/3 positions open across pair + pick), stop sizes, and
coin-flip check of the pick on the OANDA 2006-2016 period."""
import numpy as np, pandas as pd
from common import *
days, pp, A, B = pair_daily()
t = pd.read_csv('final_trades.csv', parse_dates=['entry_time', 'exit_time'])
tc = trades_in(t, *COMMON)
grid = pd.date_range('2025-05-05', '2026-10-10', freq='5min'); cnt = np.zeros(len(grid), int)
for df, a_, b_ in [(A, 'entry_time', 'exit_time'), (B, 'entry_time', 'exit_time'), (tc, 'entry_time', 'exit_time')]:
    for s, e in zip(df[a_], df[b_]):
        cnt[(grid >= s) & (grid < e)] += 1
m5 = load('M5'); live = grid.isin(m5.index)
print('share of market time with N positions open:', {k: round(float(np.mean(cnt[live] == k)) * 100, 1) for k in range(4)})
mine_open = np.zeros(len(grid), bool)
for s, e in zip(tc.entry_time, tc.exit_time): mine_open[(grid >= s) & (grid < e)] = True
print('pick in a trade', round(mine_open[live].mean() * 100, 1), '% of market time on the common window')
d = load('H1'); a48 = atr(d, 48)
st = 2.5 * a48.reindex(tc.entry_time - pd.Timedelta(hours=1)).values
print('stop distance $ on common-window entries: median', round(np.nanmedian(st), 0), 'max', round(np.nanmax(st), 0))
print('worst common-window trade', round(tc.pnl.min(), 0), 'best', round(tc.pnl.max(), 0))
