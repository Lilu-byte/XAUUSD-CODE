"""Check: fed GoldAsiaBreak's own entries, idle.bracket() reproduces H.asia() trade for trade
(M5 fixed $, M15 and H1 scaled), and the busy masks agree with the pair's trades."""
import sys; sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/idle-time/code')
import numpy as np, pandas as pd
import idle as I, harness as H

for tf, scale in (('M5', False), ('M15', True), ('H1', True)):
    A = H.asia(tf, scale=scale)
    B = I.bars(tf)
    ent = np.searchsorted(B.idx.values, A.entry_time.values)
    T = I.bracket(tf, ent, A.dir.values, tp=5, sl=50, scale=scale, gate='none')
    same = len(T) == len(A) and (T.exit_time.values == A.exit_time.values).all() and \
        np.allclose(T.pnl.values, A.pnl.values) and (T.why.values == A.why.values).all()
    print(f'{tf}: asia {len(A)} trades, engine {len(T)}, identical: {same}, '
          f'sum pnl {A.pnl.sum():.2f} vs {T.pnl.sum():.2f}')

for w in ('pair', 'm15_train', 'h1_old'):
    tf = I.tf_of(w); ba, bb = I.busy(tf); B = I.bars(tf)
    P = I.pair(w)
    # every AllAgree/AsiaBreak entry bar must be busy, the bar before an entry not (unless back-to-back)
    for k, msk in (('AllAgree', ba), ('AsiaBreak', bb)):
        e = np.searchsorted(B.idx.values, P[k].entry_time.values)
        e = e[e < len(msk)]
        print(f'  {w} {k}: entry bars busy {msk[e].mean():.3f}, share of bars busy {msk.mean():.3f}')
