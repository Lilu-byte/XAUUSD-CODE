"""expected_trades.csv (PB+SF+QB) with the EA's default shared daily closed-loss stop of $15 applied.
The replica runs each module separately with no daily stop; the EA stops all modules for the day once
today's closed P&L <= -InpDailyLoss (exits on a bar are counted before that bar's entries)."""
import sys; sys.path.insert(0,'/mnt/project-files/xauusd-microscalp/code')
from mlib import *
m = load_m1()
T = pd.read_csv('/mnt/project-files/xauusd-microscalp/ea/expected_trades.csv', parse_dates=['entry'])
T = T[T.module.isin(['PB','SF','QB'])].copy()
T['ei'] = m.index.get_indexer(T.entry); T['xi'] = T.ei + T.bars; T['day'] = T.entry.dt.normalize()
out = []
for d, g in T.groupby('day'):
    cum = 0; hb = None
    for xi, p in sorted(zip(g.xi, g.pnl)):
        cum += p
        if cum <= -15: hb = xi; break
    out.append(g if hb is None else g[g.ei < hb])
K = pd.concat(out)
K.drop(columns=['ei','xi','day']).to_csv('expected_trades_dailyloss15.csv', index=False)
print(len(T), '->', len(K))
