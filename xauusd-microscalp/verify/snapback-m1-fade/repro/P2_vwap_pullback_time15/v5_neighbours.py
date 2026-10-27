"""Diagnostic only (selects nothing): how isolated is the TEST result? Small grid around the pick on TRAIN and TEST."""
import sys, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/repro/P2_vwap_pullback_time15')
from p2lib import *
R = Rep(); m = R.m
rows = []
for k, sg, hold, mo in itertools.product((2.0, 2.5, 3.0), (0.15, None), (10, 15, 20), (1, 3)):
    raw, *_ = signal_df(m, k=k, sgate=sg)
    d, T = R.run(entry_filter(m, raw), hold=hold, mo=mo)
    a, b = stats(d, T, 'train'), stats(d, T, 'test')
    rows.append(dict(k=k, sgate=sg if sg else 0, hold=hold, mo=mo, train=a['per_day'], test=b['per_day'],
                     test_tr_day=b['trades_day'], test_long_pnl=b['long_pnl'], test_short_pnl=b['short_pnl'],
                     test_ex_top3=b['per_day_ex_top3']))
X = pd.DataFrame(rows); X.to_csv(OUT + 'v5_neighbours.csv', index=False)
print(f'{len(X)} configs. TRAIN >0: {(X.train > 0).mean():.2f}, TEST >0: {(X.test > 0).mean():.2f}, TEST >=5: {(X.test >= 5).mean():.2f}; '
      f'TEST median {X.test.median():+.2f}, range [{X.test.min():+.2f}, {X.test.max():+.2f}]; TEST ex-top-3-days >0: {(X.test_ex_top3 > 0).mean():.2f}; '
      f'TEST long-trade P&L >0: {(X.test_long_pnl > 0).mean():.2f}, short >0: {(X.test_short_pnl > 0).mean():.2f}')
print('TEST $/day by k:', X.groupby('k').test.median().round(2).to_dict(), ' by sgate:', X.groupby('sgate').test.median().round(2).to_dict(),
      ' by hold:', X.groupby('hold').test.median().round(2).to_dict(), ' by max_open:', X.groupby('mo').test.median().round(2).to_dict())
pk = X[(X.k == 2.5) & (X.sgate == 0.15) & (X.hold == 15) & (X.mo == 3)].iloc[0]
print(f'pick row: train {pk.train:+.2f} test {pk.test:+.2f}; same rule with max_open 1: '
      + str(X[(X.k == 2.5) & (X.sgate == 0.15) & (X.hold == 15) & (X.mo == 1)][['train', 'test', 'test_ex_top3']].round(2).values.tolist()))
