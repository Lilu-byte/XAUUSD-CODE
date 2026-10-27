import pandas as pd, numpy as np
d = pd.read_csv('/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv')
d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
e = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
mae = []; wk = 0
for r in e.itertuples():
    seg = d.loc[r.entry_time:r.exit_time]
    # entry_time is the bar at whose close/next open we enter? use bars strictly after entry_time through exit_time
    seg2 = d[(d.index > r.entry_time) & (d.index <= r.exit_time)]
    mae.append((r.entry - seg.low.min(), r.entry - seg2.low.min() if len(seg2) else np.nan))
    if (r.exit_time.normalize() - r.entry_time.normalize()).days >= 3 or r.exit_time.isocalendar()[1] != r.entry_time.isocalendar()[1]: wk += 1
m = np.array(mae)
print('trades', len(e), 'max adverse incl entry bar', m[:, 0].max().round(1), 'excl', np.nanmax(m[:, 1]).round(1), 'hits at 100:', (m[:, 0] >= 100).sum(), 'at 90', (m[:, 0] >= 90).sum(), 'at 80', (m[:, 0] >= 80).sum(), 'at 60', (m[:, 0] >= 60).sum())
print('weekend holds', wk, 'total pnl', e.pnl_usd.sum().round(0))
print(e.iloc[np.argmax(m[:, 0])].to_dict())
