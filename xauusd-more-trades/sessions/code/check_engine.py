"""Check: the engine with the Asian range (00:00-09:00, break, TP 5, SL 50) must reproduce
harness.asia() trade for trade on M5 (fixed $) and M15 (scaled)."""
import sys; sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/sessions/code')
import numpy as np, pandas as pd
import sessions as S, harness as H

for tf, scale in (('M5', False), ('M15', True), ('H1', True)):
    B = S.Bars(tf)
    lev = S.levels_range(B, 0, 540)
    mine = S.simulate(B, S.signals(B, lev, 540, 'break'), 5, 50, scale=scale, scale_at='entry')
    ref = H.asia(tf, scale=scale)
    m = mine.set_index('entry_time'); r = ref.set_index('entry_time')
    both = m.index.intersection(r.index)
    dp = (m.loc[both, 'pnl'] - r.loc[both, 'pnl']).abs()
    dx = (m.loc[both, 'exit_time'] != r.loc[both, 'exit_time']).sum()
    print(f'{tf}: mine {len(m)} trades, harness {len(r)}, common {len(both)}, '
          f'exit-time mismatches {dx}, max |pnl diff| {dp.max():.6f}, total {m.pnl.sum():.2f} vs {r.pnl.sum():.2f}')
    only_m = m.index.difference(r.index); only_r = r.index.difference(m.index)
    if len(only_m) or len(only_r): print('   only mine:', list(only_m[:5]), ' only harness:', list(only_r[:5]))
