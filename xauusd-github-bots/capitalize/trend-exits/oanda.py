"""Extra unseen history: OANDA XAUUSD hourly (QuantConnect/Lean repo, Data/cfd/oanda/hour/xauusd.zip), 2006-03..2016-07
(the part before David's MT5 H1 data starts). Bid candles, timestamps UTC -> shifted to MT5-style server time
(New York 17:00 = 00:00, i.e. GMT+2 winter / GMT+3 summer). D1 bars are built from the H1 bars by server date.
Same frozen rules and costs as final.py. Run:  python3 -I oanda.py /path/to/xauusd.zip"""
import sys, zipfile
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code'); sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/trend-exits')
import numpy as np, pandas as pd, tx
from gbt import atr, sma
from common import dc_sig
z = zipfile.ZipFile(sys.argv[1])
raw = pd.read_csv(z.open('xauusd.csv'), header=None, names=['t', 'o', 'h', 'l', 'c', 'v', 'ao', 'ah', 'al', 'ac', 'av'])
ts = pd.to_datetime(raw.t, format='%Y%m%d %H:%M').dt.tz_localize('UTC').dt.tz_convert('America/New_York') + pd.Timedelta(hours=7)
d = pd.DataFrame({'open': raw.o.values, 'high': raw.h.values, 'low': raw.l.values, 'close': raw.c.values},
                 index=pd.DatetimeIndex(ts.dt.tz_localize(None).values)).astype(float)
spr = pd.Series((raw.ac - raw.c).values, index=d.index)
d = d[~d.index.duplicated()].sort_index()
d = d[d.index < pd.Timestamp('2016-07-29')]           # stop where the MT5 H1 data begins
d = d[d.index.dayofweek < 5]                          # server-time weekend bars (if any) dropped
print('OANDA H1', d.index[0], d.index[-1], len(d), '| median ask-bid spread by year:',
      spr.groupby(spr.index.year).median().round(2).to_dict())
D = d.resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
reg_d = (D.close > sma(D.close, 200)).astype(float)
s = pd.Series(reg_d.values, index=D.index + pd.Timedelta(days=1))     # a D1 bar is known only after it closes
reg = s.reindex(d.index.union(s.index)).ffill().reindex(d.index).fillna(0).values > 0.5
a = atr(d, 14); sig = np.where(reg, dc_sig(d, 120), 0.0)
W = ('2007-01-01', '2016-07-29')
def hold(w):
    x = d[(d.index >= pd.Timestamp(w[0])) & (d.index < pd.Timestamp(w[1]))]; days = pd.DatetimeIndex(np.unique(x.index.normalize()))
    nights = sum(3.0 if days[k - 1].dayofweek == 2 else 1.0 for k in range(1, len(days)))
    return round((x.close.iloc[-1] - x.open.iloc[0] - 0.4 - nights * 0.126) / len(days), 2)
print('hold gold 0.01 lot', W, hold(W), '| by year', {y: hold((f'{y}-01-01', f'{y+1}-01-01')) for y in range(2007, 2017)})
for nm, kw in (('pick (pyramid +2ATR)', dict(sl=2 * a, trail_m=4.0, add_trig=2.0, max_units=2)), ('no pyramid', dict(sl=2 * a, trail_m=4.0))):
    for cost in ('flat $0.30+0.10', 'spread scaled to price'):
        sp = 0.30 if cost.startswith('flat') else float(0.30 * d.close.mean() / 4000)   # unused branch kept simple below
        if cost.startswith('flat'):
            t = tx.tsim(d, sig, a, **kw)
        else:   # cost as the same % of price as $0.40 at $4,000 would understate 2006-2012 spreads; use OANDA median ask-bid instead
            t = tx.tsim(d, sig, a, spread=float(spr[spr.index < pd.Timestamp('2016-07-29')].median()), **kw)
        r = tx.summary(t, d, *W)
        eq = tx.mtm_daily(t[t.entry_time >= pd.Timestamp(W[0])], d); eq = eq[eq.index >= pd.Timestamp(W[0])]
        yr = tx.by_year(t, d)
        print(f'== {nm} [{cost}] {W}: $/day {r["per_day"]}, trades {r["trades"]}/yr {r["tr_yr"]}, win {r["win"]}%, pf {r["pf"]}, '
              f'max_dd {r["max_dd"]}, mtm_dd {round((eq - eq.cummax()).min(), 0)}')
        print('   by year', {k: v for k, v in yr.items() if k >= 2007})
