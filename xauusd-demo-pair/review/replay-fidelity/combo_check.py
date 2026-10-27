import sys; sys.dont_write_bytecode = True
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-demo-pair/review/replay-fidelity')
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from asia_port import engine_trades, ea_trades, per_day, P, idx, days, sim
from lib import load, ema, align, SWAP_LONG
# replay CSV regenerated in memory (expected_trades.py logic, no file write)
TFS = ['M5', 'M15', 'M30', 'H1', 'H4']
b = load('M5'); bc = b.index + pd.Timedelta(minutes=5)
up = (np.vstack([align(load(tf), tf, bc, np.sign(ema(load(tf).close, 20) - ema(load(tf).close, 80)).values).fillna(0).values for tf in TFS]) > 0).all(0)
pos = pd.Series(up.astype(int), index=bc); chg = pos.diff().fillna(pos)
px = pd.Series(b.close.values, index=bc); spr = pd.Series(b.spread.values * 0.01, index=bc)
rows = []; entry = None
for t, c in chg[chg != 0].items():
    if c > 0: entry = (t, px[t] + spr[t])
    elif entry:
        nights = pd.date_range(entry[0].normalize(), t.normalize(), freq='D')[1:]
        sw = sum(3 if n.dayofweek == 3 else 1 for n in nights) * SWAP_LONG
        rows.append(dict(entry_time=entry[0], exit_time=t, pnl_usd=round(px[t] - entry[1] - sw, 2))); entry = None
R = pd.DataFrame(rows)
csv = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
print('CSV == regenerated replay:', len(R) == len(csv) and (R.entry_time.values == csv.entry_time.values).all() and np.allclose(R.pnl_usd, csv.pnl_usd))
ea = csv.groupby(csv.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0)
# H1/H4 exports aligned with M5 (same server clock)?
h1 = load('H1'); m5c = b.close; k = h1.index[(h1.index >= '2025-06-01')]
m = pd.Series(m5c.reindex(k + pd.Timedelta(minutes=55)).values, index=k)
print('H1 close == M5 xx:55 close share:', round((np.abs(h1.close.reindex(k).values - m.values) < 0.02).mean(), 4))
h4 = load('H4'); k4 = h4.index[h4.index >= '2025-06-01']
last = b.close.groupby(b.index.floor('4h')).last().reindex(k4)
print('H4 close == last M5 close in block share:', round((np.abs(h4.close.reindex(k4).values - last.values) < 0.02).mean(), 4))
for tp in (5, 8):
    rep = sim(P, 'asia_break', 'any', 540, tp, 50).pnl.reindex(days, fill_value=0)
    A = per_day(ea_trades(tp, 50))
    Ab = per_day(ea_trades(tp, 50, spread='bar'))
    # session-aware variant: close 5 min before the last bar of each day instead of 23:30
    print(f'TP{tp}: report combo EA+Asia {(ea + rep).mean():.2f}/day | with EA-rule Asia port (0.30 spread, 0.10 slip, swap) {(ea + A).mean():.2f} | with bar spreads {(ea + Ab).mean():.2f}')
