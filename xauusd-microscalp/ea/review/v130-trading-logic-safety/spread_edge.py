# How often is the spread exactly 13 points (0.13) and does the EA's float test accept it?
import sys, numpy as np, pandas as pd
m = pd.read_csv(sys.argv[1])
m['t'] = pd.to_datetime(m.time, format='%Y.%m.%d %H:%M')
tod = m.t.dt.hour * 60 + m.t.dt.minute
ins = (tod >= 900) & (tod < 1140)
print('spread points distribution in 15:00-18:59:'); print(m.spread[ins].value_counts().sort_index().head(30).to_string())
# emulate ask = bid + spread*0.01 for each bar close (bid prices), double arithmetic like MQL5
lim = 50 / 100.0 * 0.25 + 0.01 / 2
acc = rej = 0
for bid, sp in zip(m.close[ins & (m.spread == 13)].values, m.spread[ins & (m.spread == 13)].values):
    ask = round(bid + sp * 0.01, 2)          # broker quote, normalized to 2 digits
    spr = ask - bid
    if spr > lim: rej += 1
    else: acc += 1
print('13-point bars in session:', acc + rej, ' accepted by EA test:', acc, ' rejected:', rej)
print('limit value repr', repr(lim), ' 0.13 repr', repr(0.13))
# examples
for bid in (4028.45, 3650.34, 4100.07, 4000.00, 4015.87):
    ask = round(bid + 0.13, 2); print(bid, ask, repr(ask - bid), (ask - bid) > lim)
