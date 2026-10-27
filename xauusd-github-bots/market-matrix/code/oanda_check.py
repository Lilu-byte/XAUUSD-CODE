"""Older unseen history for the H4 and H1 readings: OANDA XAUUSD hourly bid candles, Mar 2006 to Jul 2016 (before
David's MT5 H1 data starts), from the QuantConnect/Lean repo already cloned (as data only) to
/tmp/claude-0/portfolio-oanda. Timestamps UTC -> server time (UTC+2, +3 during US daylight saving); H4 rebuilt
from H1 on server time. Same costs as test_rules.py (swap scaled by price/4100 before 2016).
Usage: python3 -I oanda_check.py
"""
import sys, zipfile
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import mm
from test_rules import sim, metr, rules, shift_test, OUT

ZIP = '/tmp/claude-0/portfolio-oanda/lean/Data/cfd/oanda/hour/xauusd.zip'
raw = pd.read_csv(zipfile.ZipFile(ZIP).open('xauusd.csv'), header=None,
                  names=['t', 'o', 'h', 'l', 'c', 'v', 'ao', 'ah', 'al', 'ac', 'av'])
utc = pd.to_datetime(raw.t, format='%Y%m%d %H:%M')
ny = utc.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
dst = ny.map(lambda x: x.dst() != pd.Timedelta(0)).values
srv = utc + pd.to_timedelta(np.where(dst, 3, 2), unit='h')
h1 = pd.DataFrame({'open': raw.o.values, 'high': raw.h.values, 'low': raw.l.values, 'close': raw.c.values,
                   'vol': raw.v.values.astype(float)}, index=pd.DatetimeIndex(srv))
h1 = h1[~h1.index.duplicated()].sort_index()
h1 = h1[(h1.index < pd.Timestamp('2016-07-29')) & (h1.index.dayofweek < 5)]
h4 = h1.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'vol': 'sum'}).dropna()
W = ('2007-01-01', '2016-07-28')
rows = []
for tf, d in (('H4', h4), ('H1', h1)):
    p, _ = mm.all_panels(d)
    R, _ = rules(p)
    R['Hold 0.01 lot long'] = np.ones(len(d), int)
    for name, pos in R.items():
        for mode in ('long+short', 'long only'):
            if name.startswith('Hold') and mode == 'long+short':
                continue
            ps = np.asarray(pos, int) if mode == 'long+short' else np.clip(np.asarray(pos, int), 0, 1)
            pb, t, held = sim(d, ps)
            m = metr(pb, d, W)
            row = dict(tf=tf, rule=name, mode=mode, **m)
            if name in ('MA stack 20/50/200', 'Range Osc +/-100 breakout, exit at 0') and mode == 'long only':
                row['beats_shifted'] = shift_test(d, ps, W, runs=100)
            rows.append(row)
    print(tf, 'done', flush=True)
r = pd.DataFrame(rows)
r.to_csv(OUT + 'oanda_2007_2016.csv', index=False)
pd.set_option('display.width', 200); pd.set_option('display.max_rows', 200)
print(r.to_string())
