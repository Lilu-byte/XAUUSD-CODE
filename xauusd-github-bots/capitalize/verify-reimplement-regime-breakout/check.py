import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-regime-breakout')
from indep import load, indicators, run, daily, summ

H1 = '/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv'
D1 = '/mnt/project-files/xauusd-price-action/data/XAUUSD_D1.csv'
h = load(H1); d1 = load(D1)
alld = pd.DatetimeIndex(np.unique(h.index.normalize()))
tr_days = alld[alld < '2022-01-01']; te_days = alld[alld >= '2022-01-01']

def report(t, tag):
    for lab, dd in (('train', tr_days), ('test', te_days)):
        print(tag, summ(t, dd, lab))
    p = daily(t, alld)
    print(tag, 'by year', p.groupby(p.index.year).mean().round(2).to_dict())

ind = indicators(h, d1)
t, openpos = run(h, ind)
print('open position at end of data:', openpos, '| last regime value', ind['reg'][-1])
report(t, 'PICK')
t.to_csv('/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-regime-breakout/indep_trades.csv', index=False)

# candidate's trade list, compare trade by trade
c = pd.read_csv('/mnt/project-files/xauusd-github-bots/capitalize/regime-breakout/final_trades.csv', parse_dates=['entry_time', 'exit_time'])
print('candidate trades file:', len(c), 'cols', list(c.columns))
m = t.merge(c, on=['entry_time'], how='outer', suffixes=('', '_c'), indicator=True)
print(m._merge.value_counts().to_dict())
both = m[m._merge == 'both']
print('exit_time mismatches:', (both.exit_time != both.exit_time_c).sum())
for col in ('entry', 'exit', 'pnl'):
    if col + '_c' in both:
        print(col, 'max abs diff', np.abs(both[col] - both[col + '_c']).max().round(3))
print(m[m._merge != 'both'][['entry_time', 'exit_time', 'dir', 'pnl', 'exit_time_c', '_merge']].to_string())
