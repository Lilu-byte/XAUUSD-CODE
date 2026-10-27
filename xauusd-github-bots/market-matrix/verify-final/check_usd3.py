import sys, zipfile, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm
from test_rules import sim, per_day, rules, WIN
ZIP = '/tmp/claude-0/portfolio-oanda/lean/Data/cfd/oanda/hour/xauusd.zip'
raw = pd.read_csv(zipfile.ZipFile(ZIP).open('xauusd.csv'), header=None, names=['t','o','h','l','c','v','ao','ah','al','ac','av'])
utc = pd.to_datetime(raw.t, format='%Y%m%d %H:%M')
ny = utc.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
dst = ny.map(lambda x: x.dst() != pd.Timedelta(0)).values
srv = utc + pd.to_timedelta(np.where(dst, 3, 2), unit='h')
h1 = pd.DataFrame({'open': raw.o.values, 'high': raw.h.values, 'low': raw.l.values, 'close': raw.c.values, 'vol': raw.v.values.astype(float)}, index=pd.DatetimeIndex(srv))
h1 = h1[~h1.index.duplicated()].sort_index()
h1 = h1[(h1.index < pd.Timestamp('2016-07-29')) & (h1.index.dayofweek < 5)]
h4 = h1.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'vol': 'sum'}).dropna()
OW = ('2007-01-01', '2016-07-28')
B = pd.read_pickle('/mnt/project-files/xauusd-github-bots/market-matrix/code/_bar_pnl.pkl')
def sh(pb, d, w):
    p = per_day(pb.loc[w[0]:w[1]])
    px = d.close.groupby(d.index.normalize()).last().shift().reindex(p.index)
    r = p / px
    s1 = r.mean()/r.std()*np.sqrt(252) if r.std() > 0 else np.nan
    s2 = p.mean()/p.std()*np.sqrt(252) if p.std() > 0 else np.nan
    return s1, s2, p.mean()
rows = []
for tf, od in (('H4', h4), ('H1', h1)):
    d = gbt.load(tf)
    p, _ = mm.all_panels(od); R, _ = rules(p); R['Hold 0.01 lot long'] = np.ones(len(od), int)
    for name, pos in R.items():
        for mode in ('long+short', 'long only'):
            if name.startswith('Hold') and mode == 'long+short': continue
            ps = np.asarray(pos, int) if mode == 'long+short' else np.clip(np.asarray(pos, int), 0, 1)
            o = sh(sim(od, ps)[0], od, OW)
            tr = sh(B[(tf, name, mode)], d, WIN[tf]['train']); te = sh(B[(tf, name, mode)], d, WIN[tf]['test'])
            rows.append(dict(tf=tf, rule=name, mode=mode, oanda_ret=o[0], oanda_usd=o[1], train_ret=tr[0], train_usd=tr[1], test_ret=te[0], test_usd=te[1],
                             oanda_pd=o[2], train_pd=tr[2], test_pd=te[2]))
    print(tf, flush=True)
S = pd.DataFrame(rows)
S.to_csv('usd3.csv', index=False)
out = {}
for basis in ('ret', 'usd'):
    for rnd in (False, True):
        sel = []
        for tf, g in S.groupby('tf'):
            h = g[g.rule.str.startswith('Hold')].iloc[0]
            for _, r in g[~g.rule.str.startswith('Hold')].iterrows():
                ok = True
                for per in ('oanda', 'train', 'test'):
                    a, b = r[f'{per}_{basis}'], h[f'{per}_{basis}']
                    if rnd: a, b = round(a, 2), round(b, 2)
                    if not (a >= b): ok = False
                if ok: sel.append(f"{tf}|{r.rule}|{r['mode']}")
        out[f'{basis}_rounded{rnd}'] = sel
json.dump(out, open('check_usd3.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
