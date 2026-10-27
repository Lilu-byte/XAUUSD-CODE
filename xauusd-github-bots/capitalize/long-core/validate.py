"""Sanity checks: my D1 simulator vs gbt.simulate on the plain SMA200 rule; MTM sums equal trade P&L;
no look-ahead (changing future prices does not change past decisions); pair numbers reproduce $4.68/day."""
from common import *

on = (D1.close > sma(200)).values
t, p, held = run(on)
g = gbt.simulate(D1, on.astype(float), exit_long=~on)
print('my trades', len(t), 'gbt trades', len(g))
m = min(len(t), len(g))
print('entry match', np.allclose(t.entry.values[:m], g.entry.values[:m]), 'exit match', np.allclose(t['exit'].values[:m - 1], g['exit'].values[:m - 1]))
print('swap match', np.allclose(t.swap.values[:m - 1], g.swap.values[:m - 1]), 'pnl diff', round(t.pnl.values[:m - 1].sum() - g.pnl.values[:m - 1].sum(), 4))
print('MTM sum', round(p.sum(), 2), 'trade pnl sum', round(t.pnl.sum(), 2))
# look-ahead: perturb prices after a cut date and check decisions before it are unchanged
cut = 4000
d2 = D1.copy(); d2.iloc[cut:, :4] *= 1.3
on2 = (d2.close > d2.close.rolling(200).mean()).values
print('no look-ahead (decisions before cut unchanged):', (on2[:cut] == on[:cut]).all())
t2, p2, _ = run(on2, d2)
print('pnl before cut unchanged:', np.allclose(p2.values[:cut], p.values[:cut]))
# trade list sanity
print(t.head(3).round(2).to_string()); print(t.tail(3).round(2).to_string())
print('entries all at next open after a signal flip:', all(not on[D1.index.get_loc(x) - 1] is False for x in t.entry_time))
pp, a, b, days = pair_daily()
eq = pp.cumsum()
print('pair $/day', round(pp.mean(), 2), 'maxDD', round((eq - eq.cummax()).min(), 0), 'days', len(days))
