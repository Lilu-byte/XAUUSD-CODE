"""Extra checks on the verified series: by-year, 2022-24 vs 2025-26 split, rollover-hour fills, cost sensitivity.
Usage: python3 -I extras.py (after verify.py)"""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest')
import numpy as np, pandas as pd
import gbt
from verify import metrics, with_tail, W

OUT = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest/'
S = pd.read_pickle(OUT + '_verify_daily.pkl')
res = {}
for (tf, nm), p in S['daily'].items():
    d = gbt.load(tf); dx = with_tail(d); t = S['trades'][(tf, nm)]
    w0 = W[tf]['test'][0]
    row = dict(by_year=p.groupby(p.index.year).mean().round(2).loc[2016:].to_dict(),
               y2022_24=metrics(p, dx, ('2022-01-01', '2024-12-31')), y2025_26=metrics(p, dx, ('2025-01-01', '2026-10-09')))
    tt = t[t.entry_time >= w0]
    if len(tt):
        first = dx.index.normalize() != np.r_[np.datetime64('1970-01-01'), dx.index.normalize().values[:-1]]
        fi = first[tt.ei.astype(int).values]; fx = first[tt.xi.astype(int).values]
        days = len(p.loc[w0:])
        row.update(test_trades=len(tt), entries_at_day_open=int(fi.sum()), exits_at_day_open=int(fx.sum()),
                   cost_per_day_of_extra_1usd_at_day_open=round((fi.sum() + fx.sum()) / days, 3),
                   cost_per_day_of_extra_0p20_spread=round(0.20 * len(tt) / days, 3),
                   avg_bars_held=round(float((tt.xi - tt.ei).mean()), 1))
    res[f'{tf} {nm}'] = row
    print(tf, nm, json.dumps({k: v for k, v in row.items() if k != 'by_year'}, default=str))
    print('   by year', row['by_year'])
json.dump(res, open(OUT + 'extras_results.json', 'w'), indent=1, default=str)
