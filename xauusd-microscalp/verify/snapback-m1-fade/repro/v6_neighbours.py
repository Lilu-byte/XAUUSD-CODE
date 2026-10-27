"""Diagnostic only (not a selection step; the pick stays fixed): does P1 sit on a plateau or an island?
Neighbouring thresholds / holds / max_open on TRAIN and TEST, same EA rules and costs (base spread, FAIR, next-bar open).
5 x 4 x 2 = 40 configurations."""
from common import *

R = Rep(); m = R.m
rows = []
for th in (5.0, 6.0, 7.0, 8.0, 9.0):
    s = entry_filter(m, raw_signal(m.close.values, th))
    for hold in (2, 3, 4, 5):
        for mo in (1, 2):
            d, T = R.run(s, to=hold, mo=mo)
            a = stats(d, T, 'train'); b = stats(d, T, 'test')
            rows.append(dict(th=th, hold=hold, mo=mo, train=a['per_day'], test=b['per_day'], test_tr=b['trades_day'],
                             test_ex_top3=b['per_day_ex_top3']))
X = pd.DataFrame(rows)
print(X.pivot_table(index=['th'], columns=['mo', 'hold'], values='test').round(1).to_string())
print('TRAIN:'); print(X.pivot_table(index=['th'], columns=['mo', 'hold'], values='train').round(1).to_string())
print(f'TEST share of the 40 neighbours > 0: {(X.test > 0).mean():.2f}; >= +5/day: {(X.test >= 5).mean():.2f}; '
      f'median {X.test.median():+.2f}; TEST without best 3 days > 0: {(X.test_ex_top3 > 0).mean():.2f}')
print(f'TRAIN share > 0: {(X.train > 0).mean():.2f}, median {X.train.median():+.2f}')
X.to_csv(OUT + 'v6_neighbours.csv', index=False)
