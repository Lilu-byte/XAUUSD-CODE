"""Independent check of the OANDA 2006-2016 claim. OANDA H1 bid candles (Lean repo, ~UTC) read as data only,
from a private download folder. Time zone found by matching closes to MT5 H1 on the 2016-2019 overlap."""
import sys, zipfile, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-regime-breakout')
from indep import load, indicators, run, daily

Z = '/tmp/claude-0/oanda-verify-rb/lean/Data/cfd/oanda/hour/xauusd.zip'
x = pd.read_csv(zipfile.ZipFile(Z).open('xauusd.csv'), header=None,
                names=['t', 'bo', 'bh', 'bl', 'bc', 'v', 'ao', 'ah', 'al', 'ac', 'v2'])
utc = pd.to_datetime(x.t, format='%Y%m%d %H:%M')
m = load('/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv'); d1 = load('/mnt/project-files/xauusd-price-action/data/XAUUSD_D1.csv')

def frame(idx):
    f = pd.DataFrame({'open': x.bo.values, 'high': x.bh.values, 'low': x.bl.values, 'close': x.bc.values}, index=pd.DatetimeIndex(idx))
    f = f.sort_index(); return f[~f.index.duplicated()]

cands = {'UTC+2 fixed': utc + pd.Timedelta(hours=2), 'UTC+3 fixed': utc + pd.Timedelta(hours=3),
         'NewYork+7': utc.dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.tz_localize(None) + pd.Timedelta(hours=7)}
best = None
for k, idx in cands.items():
    f = frame(idx); j = m[['close']].join(f.close.rename('oc'), how='inner')['2016-08-01':]
    e = (j.close - j.oc).abs().mean(); print(f'{k:12s} matched {len(j)} bars, mean |MT5-OANDA close| ${e:.2f}')
    if best is None or e < best[1]: best = (k, e)
o = frame(cands[best[0]]); print('using', best[0], o.index[0], o.index[-1], 'rows', len(o))
print('OANDA median bid/ask spread by year:', (x.ac - x.bc).groupby(utc.dt.year).median().round(2).loc[[2006, 2009, 2012, 2015, 2018]].to_dict())

days = pd.DatetimeIndex(np.unique(o.index.normalize()))
os_days = days[(days >= '2006-06-01') & (days <= '2016-07-28')]
ov_days = days[(days >= '2016-08-01') & (days <= '2019-02-20')]
ind = indicators(o, d1)
for lab, kw in (('pick (MOM6 gate, both)', {}), ('ungated both', dict(gate=False)), ('gated long only', dict(allow_short=False)),
                ('ungated long only', dict(gate=False, allow_short=False)), ('pick, spread 0.60', dict(spread=0.6))):
    t, _ = run(o, ind, **kw); p = daily(t, os_days); eq = p.cumsum(); y = p.groupby(p.index.year).mean()
    print(f'{lab:24s} 2006-06..2016-07 $/day {p.mean():.3f}  maxDD {(eq - eq.cummax()).min():.0f}  losing yrs 2007-15 {(y.loc[2007:2015] < 0).sum()}/9 '
          f' | overlap 16-19 {daily(t, ov_days).mean():.3f}  trades {int(((t.exit_time >= "2006-06-01") & (t.exit_time < "2016-07-29")).sum())}')
    if lab.startswith('pick ('):
        print('   by year', y.round(2).to_dict())
        pk_t = t
mi = indicators(m, d1); tm, _ = run(m, mi)
mdays = pd.DatetimeIndex(np.unique(m.index.normalize())); print('pick on MT5, same overlap', round(daily(tm, mdays[(mdays >= '2016-08-01') & (mdays <= '2019-02-20')]).mean(), 3))
# coin flip on OANDA period
c = ind['c']; reg = ind['reg']; sb = ((c > ind['hh']) & (reg > 0)) | ((c < ind['ll']) & (reg < 0))
rng = np.random.default_rng(3); cf = []
for r in range(200):
    s = np.zeros(len(c)); s[sb] = np.where(rng.random(sb.sum()) < .5, 1, -1)
    tt, _ = run(o, ind, sig=s); cf.append(daily(tt, os_days).mean())
cf = np.array(cf); pkd = daily(pk_t, os_days).mean()
print(f'OANDA coin-flip median {np.median(cf):.3f}, pick {pkd:.3f} beats {np.mean(pkd > cf) * 100:.0f}% of 200')
hs = o['2006-06-01':'2016-07-28']; td = np.unique(hs.index.normalize()); n = sum(3 if pd.Timestamp(td[k - 1]).dayofweek == 2 else 1 for k in range(1, len(td)))
print('hold 0.01 lot 2006-06..2016-07 $/day net swap', round((hs.close.iloc[-1] - hs.open.iloc[0] - 0.5 - n * 0.126) / len(os_days), 3))
