"""Is GoldAllAgree still holding a trade at the end of the M5 data? expected_trades_M5.csv lists closed trades only.
Re-runs the same rule as /mnt/project-files/xauusd-mt5/code/expected_trades.py without writing anything."""
import sys, pandas as pd, numpy as np
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from lib import load, ema, align
TFS = ['M5', 'M15', 'M30', 'H1', 'H4']
b = load('M5'); bc = b.index + pd.Timedelta(minutes=5)
T = [align(load(tf), tf, bc, np.sign(ema(load(tf).close, 20) - ema(load(tf).close, 80)).values).fillna(0).values for tf in TFS]
up = (np.vstack(T) > 0).all(0)
pos = pd.Series(up.astype(int), index=bc)
chg = pos.diff().fillna(pos)
ev = chg[chg != 0]
print('last 4 state changes:', ev.tail(4).to_dict())
print('state at last bar:', int(up[-1]), 'last M5 close time', bc[-1], 'close', b.close.values[-1])
if up[-1]:
    t0 = ev.index[-1]; e = b.close.values[np.where(bc == t0)[0][0]] + b.spread.values[np.where(bc == t0)[0][0]] * 0.01
    print('open trade since', t0, 'entry', round(e, 2), 'MTM at end', round(b.close.values[-1] - e, 2))
