"""Parity under non-default inputs (PB minutes, SF mult, QB k/hours)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea/review/signal-parity')
import ea_replica as R
from mlib import load_m1
from port import run_ea

m = load_m1(); N = len(m); tr = R.h1_trend(m).astype(np.int64)
Tc = m.index.values.astype('datetime64[s]').astype(np.int64)
rev = lambda a: np.ascontiguousarray(a[::-1])
A = [rev(x) for x in (Tc, m.open.values, m.high.values, m.low.values, m.close.values, m.tick_volume.values.astype(np.int64))]
W = 1500
for n in (1, 3, 5, 7, 10, 15, 30):
    P = run_ea(*A, tr, 1500, n=n)
    a = R.sig_pullback(m, tr, n=n)[W:].astype(int); b = P[W:, 0]
    both = (a != 0) | (b != 0)
    print(f'PB n={n:2d}: replica {(a != 0).sum():5d} mql5 {(b != 0).sum():5d} signal match {((a == b) & both).sum() / max(both.sum(), 1):.4f}')
for mult in (2.0, 4.0):
    P = run_ea(*A, tr, 1500, sfmult=mult)
    a = R.sig_spike_fade(m, mult)[W:].astype(int); b = P[W:, 1]; both = (a != 0) | (b != 0)
    print(f'SF mult={mult}: replica {(a != 0).sum()} mql5 {(b != 0).sum()} match {((a == b) & both).sum() / max(both.sum(), 1):.4f}')
for k, h0, h1 in ((0.0, 1, 22), (0.3, 8, 12)):
    P = run_ea(*A, tr, 1500, qbk=k, h0=h0, h1=h1)
    a = R.sig_quarter_fade(m, k, h0, h1)[W:].astype(int); b = P[W:, 2]; both = (a != 0) | (b != 0)
    print(f'QB k={k} {h0}-{h1}: replica {(a != 0).sum()} mql5 {(b != 0).sum()} match {((a == b) & both).sum() / max(both.sum(), 1):.4f}')
P = run_ea(*A, tr, 1500, cptrend=False)
a = R.sig_patterns(m, tr, use_trend=False)[W:].astype(int); b = P[W:, 3]; both = (a != 0) | (b != 0)
print(f'CP no trend: replica {(a != 0).sum()} mql5 {(b != 0).sum()} match {((a == b) & both).sum() / max(both.sum(), 1):.4f}')
