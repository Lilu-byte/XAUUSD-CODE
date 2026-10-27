# Port of the EA's M5Dir (M5_CANDLE) vs the replica's m5_dir rule, on M5 built from the M1 data (as the terminal does)
import sys, numpy as np, pandas as pd
m = pd.read_csv(sys.argv[1]); m.index = pd.to_datetime(m.time, format='%Y.%m.%d %H:%M')
m5 = m.resample('5min', label='left', closed='left').agg({'open': 'first', 'close': 'last'}).dropna()
t5 = m5.index.values.astype('datetime64[s]').astype(np.int64)
d5 = np.sign(m5.close - m5.open).values
t1 = m.index.values.astype('datetime64[s]').astype(np.int64)
# EA: t = r[0].time + 60; sh = bar holding t-1 (latest M5 open <= t-1); if open+300 > t use the one before
t = t1 + 60
idx = np.searchsorted(t5, t - 1, side='right') - 1           # iBarShift(exact=false): bar covering t-1
still_open = t5[idx] + 300 > t
idx2 = np.where(still_open, idx - 1, idx)
ea = np.where(idx2 >= 0, d5[np.clip(idx2, 0, None)], 0)
# replica: value of the M5 candle known at its close time (open+5min), forward-filled to t
known = pd.Series(d5, index=m5.index + pd.Timedelta(minutes=5))
at = m.index + pd.Timedelta(minutes=1)
rep = known.reindex(known.index.union(at)).ffill().reindex(at).fillna(0).values
print('bars', len(t), 'mismatches', int((ea != rep).sum()))
# look-ahead check: the M5 candle used must have closed by t
used_close = t5[np.clip(idx2, 0, None)] + 300
print('candles used that closed after t:', int((used_close > t)[idx2 >= 0].sum()))
