"""POST-HOC ONLY (not used to pick anything): every pre-listed rule on the test window and on the
common window with the pair, to show whether the training pick was unlucky or typical."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/long-core')
from rules import *
R = catalog()
pp, a, b, days = pair_daily()
tr = pd.read_csv(OUT + 'grid_train.csv').set_index('rule')
rows = []
def one(k, on):
    t, p, held = run(on, swap='fixed')
    m = metr(window(p, TEST)); core = p.reindex(days).fillna(0.0); x = pp + core; eq = x.cumsum()
    ce = core.cumsum()
    return dict(rule=k, train_score=tr.loc[k, 'score'], test_per_day=m['per_day'], test_dd=m['max_dd'], test_sharpe=m['sharpe'],
                y2022=round(window(p, ('2022-01-01', '2022-12-31')).mean(), 2), y2026=round(window(p, ('2026-01-01', '2026-12-31')).mean(), 2),
                common_core=round(core.mean(), 2), common_core_dd=round((ce - ce.cummax()).min(), 0),
                pair_plus=round(x.mean(), 2), pair_plus_dd=round((eq - eq.cummax()).min(), 0),
                losing_m=f"{(x.groupby(days.to_period('M')).sum() < 0).sum()}/18")
rows.append(one('HOLD', np.ones(len(D1), bool)))
for k, f in R.items(): rows.append(one(k, f()))
g = pd.DataFrame(rows); g.to_csv(OUT + 'posthoc_all_test.csv', index=False)
pd.set_option('display.width', 250)
print(g.sort_values('test_per_day', ascending=False).to_string(index=False))
h = g[g.rule != 'HOLD']
print('rules beating HOLD on test $/day:', (h.test_per_day > g.test_per_day[0]).sum(), 'of', len(h),
      '| on test Sharpe:', (h.test_sharpe > g.test_sharpe[0]).sum(), '| smaller test DD:', (h.test_dd > g.test_dd[0]).sum())
print('rank corr train score vs test Sharpe:', round(h.train_score.rank().corr(h.test_sharpe.rank()), 2))
