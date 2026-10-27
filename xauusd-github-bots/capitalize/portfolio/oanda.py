"""Extra unseen history: the PICK (Donchian 120/60 both ways + D1 SMA200 regime) on OANDA XAUUSD hourly bid
candles, Mar 2006 .. Jul 2016 (before the MT5 H1 data starts). Data from the QuantConnect/Lean repo,
downloaded to /tmp/claude-0/portfolio-oanda (read as data only). Timestamps ~UTC -> server time
(UTC+2, +3 while US daylight saving is on), D1 bars rebuilt from H1 on server days."""
import sys, zipfile
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd
from gbt import simulate, daily, atr, sma
from common import maxdd, losing_months
ZIP = '/tmp/claude-0/portfolio-oanda/lean/Data/cfd/oanda/hour/xauusd.zip'
raw = pd.read_csv(zipfile.ZipFile(ZIP).open('xauusd.csv'), header=None,
                  names=['t', 'o', 'h', 'l', 'c', 'v', 'ao', 'ah', 'al', 'ac', 'av'])
utc = pd.to_datetime(raw.t, format='%Y%m%d %H:%M')
ny = utc.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
dst = ny.map(lambda x: x.dst() != pd.Timedelta(0)).values
srv = utc + pd.to_timedelta(np.where(dst, 3, 2), unit='h')
d = pd.DataFrame({'open': raw.o.values, 'high': raw.h.values, 'low': raw.l.values, 'close': raw.c.values,
                  'spread': (raw.ac - raw.c).values}, index=pd.DatetimeIndex(srv))
d = d[~d.index.duplicated()].sort_index()
d = d[d.index < pd.Timestamp('2016-07-29')]
d = d[d.index.dayofweek < 5]           # drop the odd Saturday stub, as MT5 shows none
print('OANDA H1', d.index[0], d.index[-1], len(d), '| median spread by year', d.spread.groupby(d.index.year).median().round(2).to_dict())
D = d.resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
up_d = (D.close > sma(D.close, 200)).astype(float)
valid_d = sma(D.close, 200).notna()
# closed D1 bar -> available from the next server day 00:00
s = pd.Series(up_d.values, index=D.index + pd.Timedelta(days=1))
v = pd.Series(valid_d.values.astype(float), index=D.index + pd.Timedelta(days=1))
up = s.reindex(d.index.union(s.index)).ffill().reindex(d.index).values > 0.5
ok = v.reindex(d.index.union(v.index)).ffill().reindex(d.index).values > 0.5
a = atr(d, 48)
hh = d.high.shift().rolling(120).max(); ll = d.low.shift().rolling(120).min()
xh = d.high.shift().rolling(60).max(); xl = d.low.shift().rolling(60).min()
sig = np.where(d.close > hh, 1, np.where(d.close < ll, -1, 0)).astype(float)
raw_sig = sig.copy(); raw_sig[~ok] = 0
sig[(sig > 0) & ~up] = 0; sig[(sig < 0) & up] = 0; sig[~ok] = 0
kw = dict(sl=2.5 * a, exit_long=(d.close < xl).values, exit_short=(d.close > xh).values)
med_spread = float(d.spread.median())
for lab, sg in [('PICK (SMA200 regime)', sig), ('raw Donchian 120/60', raw_sig)]:
    for cost_lab, sp in [('flat $0.30 spread', 0.30), (f'OANDA median spread ${med_spread:.2f}', med_spread)]:
        t = simulate(d, sg, spread=sp, **kw)
        p = daily(t, d); p = p[p.index >= pd.Timestamp('2007-01-01')]
        t = t[t.exit_time >= pd.Timestamp('2007-01-01')]
        nm, nmt, _ = losing_months(p)
        print(f'{lab} | {cost_lab}: $/day {p.mean():.2f}, trades {len(t)}, win {100 * (t.pnl > 0).mean():.0f}%, '
              f'long {t.pnl[t.dir > 0].sum():.0f} short {t.pnl[t.dir < 0].sum():.0f}, dd {maxdd(p):.0f}, losing months {nm}/{nmt}')
        print('    by year', p.groupby(p.index.year).mean().round(2).to_dict())
# hold gold 2007-01 .. 2016-07 for scale
dd_ = d[d.index >= pd.Timestamp('2007-01-01')]
sg = np.zeros(len(dd_)); sg[0] = 1; xl2 = np.zeros(len(dd_), bool); xl2[-2] = True
th = simulate(dd_, sg, exit_long=xl2)
print('hold 0.01 lot 2007-01..2016-07 incl swap: $/day', round(daily(th, dd_).mean(), 2), 'gross', round(th.gross.sum()), 'swap', round(th.swap.sum()))
