"""XAUUSD_PDH_Break v1.0 replay (18 Oct 2026), line by line from source/XAUUSD_PDH_Break.mq5.

Rule: on M15 or H1, a closed bar closes above the previous server day's high while the bar before it
closed at or below it, both bars in today's server day, first time that day (the day is used up even
if no trade is placed). Buy at the next bar's open (ask), stop = ask - 1 x ATR14 (Wilder) of the
signal bar, target = ask + 2 x ATR, close at the open of the bar 32 (M15) / 24 (H1) bars after entry.
One position at a time; while it is open no new signal is looked for.
Costs (project convention): spread $0.30 + slippage $0.10 on market fills and stops, swap $0.126/night
long, triple into Thursday. Stop checked before target inside a bar.
Sizing: lots='fixed' -> 0.01 lot; lots='ea' -> 0.5% of balance / (ATR x $1 per 0.01 lot), floored to
0.01, trade skipped when below 0.01 (what the EA does), balance compounding from start_bal.
"""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd

D = '/mnt/project-files/'
FILES = {'M15': D + 'xauusd-intraday/data/XAUUSD_M15.csv', 'H1': D + 'xauusd-price-action/data/XAUUSD_H1.csv',
         'D1': D + 'xauusd-price-action/data/XAUUSD_D1.csv', 'M5': D + 'xauusd-intraday/data/XAUUSD_M5.csv'}
SPREAD, SLIP, SWAP_L = 0.30, 0.10, 0.126


def load(tf):
    d = pd.read_csv(FILES[tf]); d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    return d[['open', 'high', 'low', 'close', 'spread']].astype(float)


def wilder_atr(d, n=14):
    pc = d.close.shift()
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def nights(e, x):
    k = pd.date_range(pd.Timestamp(e).normalize(), pd.Timestamp(x).normalize(), freq='D')[1:]
    return sum(3 if z.dayofweek == 3 else 1 for z in k)


def run(tf='M15', stop_atr=1.0, tgt_atr=2.0, hold=None, lots='fixed', start_bal=3000.0, risk=0.5, d=None):
    d = load(tf) if d is None else d
    hold = hold or (32 if tf == 'M15' else 24)
    d1 = load('D1')
    day = d.index.normalize()
    # previous server day's high = high of the last D1 bar before today
    pdh_s = pd.Series(d1.high.values, index=d1.index).shift(1)
    pdh = pdh_s.reindex(day).values
    a = wilder_atr(d).values
    o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    t = d.index; dayv = day.values
    rows = []; bal = start_bal; fired = None; i = 2; n = len(d)
    while i < n:
        # signal on closed bar i-1, bar i-2 also today; decide at open of bar i
        sday = dayv[i]
        if (fired != sday and dayv[i - 1] == sday and dayv[i - 2] == sday and np.isfinite(pdh[i])
                and c[i - 1] > pdh[i] and c[i - 2] <= pdh[i]):
            fired = sday
            atr = a[i - 1]
            ask = o[i] + SPREAD
            if lots == 'fixed':
                q = 1.0
            else:
                q = np.floor(bal * risk / 100 / atr + 1e-9)   # in 0.01-lot units ($1 per $1 per unit)
                if q < 1: i += 1; continue
            ent = ask + SLIP; sl = ask - stop_atr * atr; tp = ask + tgt_atr * atr
            px = None; why = None
            j = i
            while j < n:
                if j - i >= hold:          # time exit at the open of bar entry+hold
                    px, why = o[j] - SLIP, 'time'; break
                if j > i and o[j] <= sl: px, why = o[j] - SLIP, 'stop'; break
                if l[j] <= sl: px, why = sl - SLIP, 'stop'; break
                if j > i and o[j] >= tp: px, why = o[j], 'target'; break
                if h[j] >= tp: px, why = tp, 'target'; break
                j += 1
            if px is None: break
            sw = nights(t[i], t[j]) * SWAP_L
            pnl = (px - ent - sw) * q
            bal += pnl
            rows.append(dict(entry_time=t[i], exit_time=t[j], dir=1, entry_px=ent, exit_px=px, lots=q / 100,
                             atr=atr, R=(px - ent - sw) / (stop_atr * atr), pnl=pnl, why=why))
            # EA: a bar with the exit can't give a signal (position still open at that new-bar check)
            i = j + 1
            continue
        i += 1
    return pd.DataFrame(rows)


if __name__ == '__main__':
    for tf in ('M15', 'H1'):
        for lots in ('fixed', 'ea'):
            r = run(tf, lots=lots)
            print(tf, lots, len(r), 'R/trade %.3f' % r.R.mean(), '$ %.0f' % r.pnl.sum(),
                  'win %.2f' % (r.pnl > 0).mean(), r.why.value_counts().to_dict(),
                  r.entry_time.min().date(), r.entry_time.max().date())
