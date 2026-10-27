import sys, zipfile, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import mm
from test_rules import sim, per_day, rules
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
out = {'h1_first': str(h1.index[0]), 'h1_last': str(h1.index[-1]), 'vol_sum': float(h1.vol.sum())}
def m(pb, d):
    p = per_day(pb.loc[W[0]:W[1]])
    px = d.close.groupby(d.index.normalize()).last().shift().reindex(p.index)
    r = p / px
    eq = p.cumsum()
    return [float(r.mean()/r.std()*np.sqrt(252)), float(p.mean()), float((eq-eq.cummax()).min()), str(p.index[0]), str(p.index[-1])]
for tf, d, names in (('H4', h4, ['MA stack 20/50/200', 'MACD line sign']), ('H1', h1, ['Range Osc +/-100 breakout, exit at 0', 'All panels: 5+ of 7 agree'])):
    p, _ = mm.all_panels(d)
    R, _ = rules(p)
    for n in names:
        out[f'{tf}|{n}|lo'] = m(sim(d, np.clip(np.asarray(R[n], int), 0, 1))[0], d)
    out[f'{tf}|hold'] = m(sim(d, np.ones(len(d), int))[0], d)
json.dump(out, open('check_oanda.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
