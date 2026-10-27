import numpy as np, pandas as pd, sys
d = pd.read_csv('/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv')
d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M'); d = d[d.index.dayofweek < 5]
o, h, l, c = (d[k].values for k in ('open', 'high', 'low', 'close')); sc = c / 4000
dates = d.index.normalize(); u, day = np.unique(dates.values, return_inverse=True)
tod = (d.index.hour * 60 + d.index.minute).values
hi = d.high.where(tod < 540).groupby(dates).cummax().groupby(dates).ffill().values
lo = d.low.where(tod < 540).groupby(dates).cummin().groupby(dates).ffill().values
sig = np.where(tod >= 540, np.where(c > hi, 1, np.where(c < lo, -1, 0)), 0)
SP, SL_ = .30, .10
def run(endf, stale_close=False, first_only=False, tp=5, sl=50):
    n = len(c); pos = 0; cur = -1; nt = 0; trades = []; firstseen = False
    for i in range(n):
        END = endf(i)
        if day[i] != cur: cur = day[i]; nt = 0; firstseen = False
        if pos != 0:
            ex = False
            if pos == 1:
                slp = ent - sld; tpp = ent + tpd
                if o[i] <= slp: px = o[i] - SL_ * es; ex = 'sl'
                elif l[i] <= slp: px = slp - SL_ * es; ex = 'sl'
                elif h[i] >= tpp: px = tpp; ex = 'tp'
                elif tod[i] >= END: px = c[i] - SL_ * es; ex = 'eod'
                elif stale_close and day[i] != eday: px = o[i] - SL_ * es; ex = 'stale'
                pnl = px - ent
            else:
                a = SP * es; slp = ent + sld; tpp = ent - tpd
                if o[i] + a >= slp: px = o[i] + a + SL_ * es; ex = 'sl'
                elif h[i] + a >= slp: px = slp + SL_ * es; ex = 'sl'
                elif l[i] + a <= tpp: px = tpp; ex = 'tp'
                elif tod[i] >= END: px = c[i] + a + SL_ * es; ex = 'eod'
                elif stale_close and day[i] != eday: px = o[i] + a + SL_ * es; ex = 'stale'
                pnl = ent - px
            if ex:
                pos = 0; trades.append((u[eday], d.index[ei], d.index[i], pos_, pnl / es, ex, day[i] - eday)); continue
        if sig[i] != 0 and tod[i] >= 540 and not firstseen:
            first_bar = True
        else: first_bar = False
        if pos == 0 and nt < 1 and tod[i] >= 540 and tod[i] < END - 15 and sig[i] != 0 and (not first_only or not firstseen):
            es = sc[i]; pos = int(sig[i]); pos_ = pos; nt += 1; tpd = tp * es; sld = sl * es; eday = day[i]; ei = i
            ent = c[i] + (SP + SL_) * es if pos == 1 else c[i] - SL_ * es
        if sig[i] != 0 and tod[i] >= 540: firstseen = True
    return pd.DataFrame(trades, columns=['day', 'entry', 'exit', 'dir', 'pnl', 'how', 'nights'])
lo_, hi_ = pd.Timestamp('2025-05-06'), pd.Timestamp('2026-10-10')
def rep(name, t):
    t = t[(t.exit >= lo_) & (t.exit < hi_)]
    car = t[t.nights > 0]
    print(f'{name}: trades {len(t)} total {t.pnl.sum():.0f} carried {len(car)} (since Mar26 {(car.entry >= "2026-03-01").sum()}, max nights {car.nights.max() if len(car) else 0})', t.how.value_counts().to_dict())
    return t
base = rep('orig 23:30', run(lambda i: 1410))
car = base[base.nights > 0]; print(car[['entry', 'exit', 'dir', 'pnl', 'how', 'nights']].to_string())
rep('fixed 22:40', run(lambda i: 1360))
rep('fixed 22:40 + stale', run(lambda i: 1360, True))
spec = np.where(d.index < pd.Timestamp('2026-03-09'), 1440, 1380)   # weekly spec: 24:00 before, 23:00 after
rep('sess-10 + stale', run(lambda i: min(1410, spec[i] - 10), True))
rep('sess-10 no stale', run(lambda i: min(1410, spec[i] - 10), False))
rep('22:40 backstop+sess+stale', run(lambda i: min(1360, spec[i] - 10), True))
rep('orig, first-only', run(lambda i: 1410, False, True))
print(base[base.day.isin(pd.to_datetime(['2025-07-03', '2025-07-04', '2026-02-27']))][['entry', 'exit', 'dir', 'pnl', 'how']].to_string())
# first break not tradeable in replay? count days where first break bar >= END-15
early = pd.to_datetime(['2025-05-26','2025-06-19','2025-07-04','2025-09-01','2025-11-28','2025-12-24','2026-01-19','2026-02-16','2026-02-26','2026-05-25','2026-06-19','2026-07-03','2026-09-07'])
print('trades on early-close days', base[base.day.isin(early)][['entry','exit','pnl','how','nights']].to_string())
