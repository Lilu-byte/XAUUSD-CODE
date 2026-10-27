"""Unit check: cv3.bracket_pnl must equal harness per-trade P&L for non-overlapping entries."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model'); sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from cv3 import bracket_pnl
from mlib import *
H = Harness(); spr = H._spr['base']
for tp, sl, to in ((1.0, 3.0, 10), (0.5, 1.0, 5), (0.1, 2.0, 3)):
    L, S = bracket_pnl(H.o, H.h, H.l, H.c, spr, H.tod, H.day, tp, sl, to, END_TOD)
    for s, P in ((1, L), (-1, S)):
        sig = np.zeros(len(H.c), int); sig[np.arange(200, len(sig), 41)] = s
        d, t = H.run(sig, tp, sl, timeout=to, max_open=1)
        ii = H.m1.index.get_indexer(t.entry)
        print(tp, sl, to, s, 'trades', len(t), 'max abs diff', np.nanmax(np.abs(t.pnl.values - P[ii])).round(6))
