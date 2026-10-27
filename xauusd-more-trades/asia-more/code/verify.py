"""Check that asia_x() with every extension off reproduces harness.asia() trade for trade,
and that sim_fixed() reproduces asia_x()'s trades from their entry times and directions.
Usage: python3 -I verify.py"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/asia-more/code')
import numpy as np, pandas as pd
import asia_more as A
H = A.H

COLS = ['entry_time', 'exit_time', 'dir', 'entry_px', 'exit_px', 'why', 'pnl']


def same(a, b):
    if len(a) != len(b): return f'different counts {len(a)} vs {len(b)}'
    a = a[COLS].reset_index(drop=True); b = b[COLS].reset_index(drop=True)
    bad = []
    for k in COLS:
        if a[k].dtype.kind == 'f':
            if not np.allclose(a[k].values, b[k].values, atol=1e-9, rtol=0): bad.append(k)
        elif not (a[k].values == b[k].values).all(): bad.append(k)
    return 'identical' if not bad else f'differs in {bad}'


for tf, scale in (('M5', False), ('M15', True), ('H1', True)):
    ref = H.asia(tf, scale=scale)
    mine = A.asia_x(tf, scale=scale)
    print(f'{tf} scale={scale}: harness {len(ref)} trades, copy {len(mine)} -> {same(ref, mine)}')
    ents = list(zip(mine.entry_time, mine.dir, mine.tp, mine.sl))
    fx = A.sim_fixed(tf, ents, scale=scale)
    mm = mine.assign(why=mine.why.replace('next open', 'EOD'))
    print(f'   sim_fixed from the same entries -> {same(mm, fx)}')

# the extended engine, one re-arm version, against sim_fixed on its own entries
x = A.asia_x('M15', scale=True, rearm='tp', max_trades=3, fresh='newext', sar='break')
fx = A.sim_fixed('M15', list(zip(x.entry_time, x.dir, x.tp, x.sl)), scale=True)
print('M15 re-arm+sar version', x.kind.value_counts().to_dict(), '-> sim_fixed', same(x.assign(why=x.why.replace('next open', 'EOD')), fx))
