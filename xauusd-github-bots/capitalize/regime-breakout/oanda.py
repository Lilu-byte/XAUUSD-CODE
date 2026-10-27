"""Extra unseen history: OANDA XAUUSD H1 (QuantConnect/Lean Data/cfd/oanda/hour, bid candles, UTC stamps),
converted to MT5 server time (New York time + 7h = GMT+2 winter / GMT+3 summer). Read as data only.
Regimes still come from the MT5 D1 file (2004-) through htf(), exactly as live.
Scores 2006-06..2016-07 (before the MT5 H1 file starts); the 2016-08..2019-02 overlap is used to check the feed."""
import sys, numpy as np, pandas as pd
from common import *
F = '/tmp/claude-0/oanda-regime-breakout/csv/xauusd.csv'
x = pd.read_csv(F, header=None, names=['t', 'bo', 'bh', 'bl', 'bc', 'v', 'ao', 'ah', 'al', 'ac', 'v2'])
ts = pd.to_datetime(x.t, format='%Y%m%d %H:%M').dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.tz_localize(None) + pd.Timedelta(hours=7)
o = pd.DataFrame({'open': x.bo.values, 'high': x.bh.values, 'low': x.bl.values, 'close': x.bc.values,
                  'spread': (x.ac - x.bc).values, 'vol': 0.0}, index=pd.DatetimeIndex(ts)).sort_index()
o = o[~o.index.duplicated()]
print('OANDA H1 rows', len(o), o.index[0], o.index[-1], '| median spread $', round(o.spread.median(), 2),
      'by year', o.spread.groupby(o.index.year).median().round(2).loc[[2006, 2010, 2014, 2018]].to_dict())
# feed check on the overlap
m = load('H1'); j = m.join(o[['close']].rename(columns={'close': 'oc'}), how='inner')
j = j['2016-08-01':]
for lag in [-1, 0, 1]:
    jj = m.close.to_frame().join(o.close.shift(lag).rename('oc'), how='inner')['2016-08-01':]
    print(f'lag {lag:+d}h: matched {len(jj)} bars, mean |MT5-OANDA| close ${(jj.close - jj.oc).abs().mean():.2f}')
OS = ('2006-06-01', '2016-07-28')
R = d1_regimes(); rows = []
for bn in ['MAXI', 'DON']:
    d, sig0, kw = base(bn, o)
    for lo in [False, True]:
        for rg in ['NONE', 'MA200', 'MOM12', 'MOM6', 'ADX25', 'VOL', 'MA+MOM12']:
            t = simulate(d, gate(d, sig0, rg, lo, R), **kw); p = window_daily(t, d, *OS); y = years(p)
            pin = window_daily(t, d, '2016-08-01', '2019-02-20')
            rows.append(dict(base=bn, dir='long' if lo else 'both', regime=rg, oos_per_day=round(p.mean(), 2), dd=summarize(p)['max_dd'],
                             lose_yrs=int((y.loc[2007:2015] < 0).sum()), overlap_16_19=round(pin.mean(), 2), **{str(k): v for k, v in y.items()}))
res = pd.DataFrame(rows); pd.set_option('display.width', 260); pd.set_option('display.max_columns', 30)
print(res.to_string(index=False)); res.to_csv('oanda_2006_2016.csv', index=False)
hd = o[OS[0]:OS[1]]
print('hold 0.01 lot 2006-06..2016-07 (net swap, gross):', hold_per_day(hd, *OS))
# same-years MT5 check of the pick on the overlap
d, s0, kw = base('DON'); t = simulate(d, gate(d, s0, 'MOM6', False, R), **kw)
print('pick on MT5 2016-08..2019-02:', round(window_daily(t, d, '2016-08-01', '2019-02-20').mean(), 2))
# coin-flip on the OANDA period for the pick
d, s0, kw = base('DON', o); sg = gate(d, s0, 'MOM6', False, R); nz = sg != 0; rng = np.random.default_rng(1); cf = []
for _ in range(100):
    r = sg.copy(); r[nz] = np.where(rng.random(nz.sum()) < .5, 1.0, -1.0)
    cf.append(window_daily(simulate(d, r, **kw), d, *OS).mean())
cf = np.array(cf); pk = window_daily(simulate(d, sg, **kw), d, *OS)
print('OANDA pick', summarize(pk), f'coin-flip median {np.median(cf):.2f}, pick beats {np.mean(cf < pk.mean())*100:.0f}%')
