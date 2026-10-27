"""Check aa_more against harness: with defaults it must give harness.allagree's trades, and the
scaled ones pair_parts uses, on every base timeline (M5, M15, H1). Also checks short side and
need-k against harness.allagree(side=-1 / need=k).
Usage: python3 -I verify.py"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/allagree-more/code')
import numpy as np
import aa_more as A
H = A.H

COLS = ['entry_time', 'exit_time', 'dir', 'entry_px', 'exit_px', 'pnl']


def same(a, b):
    if len(a) != len(b): return f'len {len(a)} vs {len(b)}'
    bad = 0
    for k in COLS:
        x, y = a[k].values, b[k].values
        bad += int((x != y).sum()) if k in ('entry_time', 'exit_time', 'dir') else int((~np.isclose(x.astype(float), y.astype(float), atol=1e-9)).sum())
    return f'{len(a)} trades, {bad} differences'


if __name__ == '__main__':
    for w in ('pair', 'm15_train', 'h1_old'):
        P = H.pair_parts(w)['AllAgree']
        print(w, 'baseline vs pair_parts:', same(A.baseline_aa(w).reset_index(drop=True), P.reset_index(drop=True)))
    for base, tfs in (('M5', ('M5', 'M15', 'M30', 'H1', 'H4')), ('M15', ('M15', 'M30', 'H1', 'H4')), ('H1', ('H1', 'H4'))):
        for kw in (dict(side=-1), dict(need=len(tfs) - 1), dict(fast=10, slow=40)):
            h = H.allagree(base, tfs, **kw)
            m = A.trades(base, A.agree(base, tfs, (kw.get('fast', 20), kw.get('slow', 80)), kw.get('need'), kw.get('side', 1)),
                         side=kw.get('side', 1), scale=False)
            print(base, kw, same(m.reset_index(drop=True), h.reset_index(drop=True)))
