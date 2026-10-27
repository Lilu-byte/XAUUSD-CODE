"""Step 1: reproduce the long-core headline numbers with my own simulator, cross-checked against gbt.simulate."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-overfit-long-core')
from vsim import *

D1 = gbt.load('D1'); c = D1.close
on = golden(c, 50, 200)
p, held, t = mtm(on, D1)
ph, hh, th = mtm(np.ones(len(D1), bool), D1)
ps, _, _ = mtm(on, D1, 'scaled', 0.126 * 365 / 4100 * 100)
phs, _, _ = mtm(np.ones(len(D1), bool), D1, 'scaled', 0.126 * 365 / 4100 * 100)

# cross-check realized trades with gbt.simulate
g = gbt.simulate(D1, on.astype(float), exit_long=~on)
closed = t[~t.open_at_end]
k = min(len(closed), len(g))
print('trades mine', len(t), '(closed', len(closed), ') gbt', len(g),
      '| entry match', np.allclose(closed.entry.values[:k], g.entry.values[:k]),
      'exit match', np.allclose(closed['exit'].values[:k], g['exit'].values[:k]),
      'pnl match', np.allclose(closed.pnl.values[:k], g.pnl.values[:k]))
print('MTM sum == trade pnl sum:', round(p.sum(), 2), round(t.pnl.sum(), 2))

for lbl, w in (('TRAIN_A 2005-04..2015 (scaled swap 1.12%/yr)', TRAIN_A),):
    print(lbl, 'rule', m(win(ps, w), c), '| hold', m(win(phs, w), c))
for lbl, w in (('TRAIN_B 2016-07..2021', TRAIN_B), ('TEST 2022..2026-10', TEST)):
    print(lbl, 'rule', m(win(p, w), c), '| hold', m(win(ph, w), c), '| in-market', round(win(held, w).mean() * 100), '%')
by = pd.DataFrame({'rule': p.loc['2016-07-29':].groupby(p.loc['2016-07-29':].index.year).mean(),
                   'hold': ph.loc['2016-07-29':].groupby(ph.loc['2016-07-29':].index.year).mean()}).round(2)
print(by.T.to_string())
tt = t[t.exit_time >= TEST[0]]
print('test-window trades:'); print(tt.round(2).to_string(index=False))
# share of test profit from the single biggest trade (MTM inside the test window)
big = tt.loc[tt.pnl.idxmax()]
inside = win(p, TEST)
seg = inside.loc[big.entry_time:big.exit_time].sum()
print(f'test total ${inside.sum():.0f}; MTM of the Dec-2023..Jun-2026 trade inside test ${seg:.0f} = {seg / inside.sum() * 100:.0f}% of it')
print(f'test excess vs hold ${win(p - ph, TEST).mean():.2f}/day; what flat periods avoided: hold P&L on days rule flat '
      f'${win(ph, TEST)[~win(held, TEST).values].sum():.0f}')

# common window and pair
pp, a, b, days = pair_daily()
core = p.reindex(days).fillna(0.0); hc = ph.reindex(days).fillna(0.0)
print('M5 days missing in D1:', len(set(days) - set(D1.index)))
for lbl, x in (('pair', pp), ('core MTM', core), ('pair+core', pp + core), ('hold', hc), ('pair+hold', pp + hc)):
    mo = x.groupby(x.index.to_period('M')).sum()
    print(f'  COMMON {lbl:10s}', m(x), 'worst month', round(mo.min(), 0))
print('  corr core/pair daily', round(np.corrcoef(core, pp)[0, 1], 2))
print('current state: last close', c.iloc[-1], 'SMA50', round(c.rolling(50).mean().iloc[-1], 0), 'SMA200',
      round(c.rolling(200).mean().iloc[-1], 0), 'long?', bool(on[-1]))
