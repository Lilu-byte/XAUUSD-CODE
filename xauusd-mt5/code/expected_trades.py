"""Replays the EA's rule bar by bar on the MT5 export (M5 timeline) and lists the
trades it should take, so a Strategy Tester run can be compared against it.
One 0.01 lot = 1 oz, so P&L in $ = price change. Entries/exits at the M5 close
where the signal flips (the EA trades on the first tick after that close)."""
import sys, pandas as pd, numpy as np
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from lib import load, ema, MIN, align, SWAP_LONG

TFS = ['M5', 'M15', 'M30', 'H1', 'H4']
b = load('M5'); bc = b.index + pd.Timedelta(minutes=5)
T = []
for tf in TFS:
    d = load(tf)
    T.append(align(d, tf, bc, np.sign(ema(d.close, 20) - ema(d.close, 80)).values).fillna(0).values)
up = (np.vstack(T) > 0).all(0)
pos = pd.Series(up.astype(int), index=bc)          # decided at each M5 close
px = pd.Series(b.close.values, index=bc); spr = pd.Series(b.spread.values * 0.01, index=bc)
chg = pos.diff().fillna(pos)
rows = []; entry = None
for t, c in chg[chg != 0].items():
    if c > 0: entry = (t, px[t] + spr[t])            # buy at ask
    elif entry:
        nights = pd.date_range(entry[0].normalize(), t.normalize(), freq='D')[1:]
        sw = sum(3 if n.dayofweek == 3 else 1 for n in nights) * SWAP_LONG   # rollover into Thursday counts 3x
        rows.append(dict(entry_time=entry[0], entry=round(entry[1], 2), exit_time=t, exit=px[t],
                         pnl_usd=round(px[t] - entry[1] - sw, 2), hours=round((t - entry[0]).total_seconds() / 3600, 1)))
        entry = None
tr = pd.DataFrame(rows)
tr.to_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', index=False)
tr['year'] = tr.entry_time.dt.year
print(tr.groupby('year').agg(trades=('pnl_usd', 'size'), win_rate=('pnl_usd', lambda x: (x > 0).mean()),
                             pnl_usd=('pnl_usd', 'sum'), avg_hours=('hours', 'mean')).round(2))
print('total $ per 0.01 lot:', tr.pnl_usd.sum().round(2), '| trades', len(tr), '| win rate', round((tr.pnl_usd > 0).mean(), 2))
eq = 3000 + tr.pnl_usd.cumsum(); print('worst closed-trade drawdown on $3,000:', round(((eq - eq.cummax()) / eq.cummax()).min() * 100, 1), '%')
print('biggest loss', tr.pnl_usd.min(), 'biggest win', tr.pnl_usd.max())
print('state at last bar:', dict(zip(TFS, [int(x[-1]) for x in T])), '->', 'LONG' if up[-1] else 'FLAT')
print(tr.tail(5).to_string())
