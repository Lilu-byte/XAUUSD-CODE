"""Check tx.tsim against gbt.simulate on configurations both can express."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code'); sys.path.insert(0, '.')
import numpy as np, pandas as pd, gbt, bots, tx
def cmp(name, t1, t2):
    a = t1[['entry_time', 'exit_time', 'dir', 'entry', 'exit', 'pnl']].reset_index(drop=True)
    b = t2[['entry_time', 'exit_time', 'dir', 'entry', 'exit', 'pnl']].reset_index(drop=True)
    same = len(a) == len(b) and (a.entry_time == b.entry_time).all() and np.allclose(a.pnl, b.pnl)
    print(f'{name}: gbt {len(a)} trades pnl {a.pnl.sum():.2f} | tx {len(b)} trades pnl {b.pnl.sum():.2f} | identical={same}')
    if not same:
        m = a.merge(b, on='entry_time', how='outer', suffixes=('_g', '_t'), indicator=True)
        diff = m[(m._merge != 'both') | ~np.isclose(m.pnl_g.fillna(0), m.pnl_t.fillna(0))]
        print('   differing rows:', len(diff)); print(diff.head(6).to_string())
d, sig, kw = bots.maxi()
a = gbt.atr(d, 14)
cmp('maxi sl/tp', gbt.simulate(d, sig, **kw), tx.tsim(d, sig, a, sl=kw['sl'], tp=kw['tp'], allow_same=True))
cmp('maxi sl/tp (no same-bar re-entry)', gbt.simulate(d, sig, **kw), tx.tsim(d, sig, a, sl=kw['sl'], tp=kw['tp']))
d, sig, kw = bots.donchian()
cmp('donchian', gbt.simulate(d, sig, **kw), tx.tsim(d, sig, gbt.atr(d, 48), sl=kw['sl'], exit_long=kw['exit_long'], exit_short=kw['exit_short'], allow_same=True))
