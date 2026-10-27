"""Unit check: ml2.bracket_pnl2 must equal mlib v2 per-trade P&L (FAIR and OHLC fills) for non-overlapping entries,
including entries near the end of the session."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *
H = Harness(); ok = tradeable2(H.m1)
for fill in ('FAIR', 'OHLC'):
    for tp, sl, to in ((1.0, 3.0, 10), (0.5, 1.0, 5), (0.1, 2.0, 30), (0.3, 0.3, 2)):
        L, S, _ = bracket_pnl2(H.o, H.h, H.l, H.c, H._spr['base'], H.tod, H.day, H.last, tp, sl, to, FILL[fill])
        for s, P in ((1, L), (-1, S)):
            for off in (200, 1337):
                sig = np.zeros(len(H.c), int); sig[np.arange(off, len(sig), 37)] = s
                d, t = H.run(sig, tp, sl, timeout=to, max_open=1, fill=fill)
                ii = H.m1.index.get_indexer(t.entry)
                assert ok[ii].all()
                print(fill, tp, sl, to, s, off, 'trades', len(t), 'max abs diff', float(np.nanmax(np.abs(t.pnl.values - P[ii]))),
                      'entries allowed but not traded', int((ok & (sig != 0)).sum() - len(t)))
# entries the harness refuses must be NaN after masking
print('tradeable share', ok.mean().round(4), 'last allowed tod', H.tod[ok].max(), 'first', H.tod[ok].min())
