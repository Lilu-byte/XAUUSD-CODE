"""POST-HOC diagnosis after the single TEST scoring (no selection from this): where the per-trade move went.
Average fade move by bar after the signal (bid closes, before spread), TRAIN vs TEST, for the pick triggers,
and the average spread paid ('base')."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch')
from feats import *
from simlib import EASim
E = EASim(); m = E.H.m1; f = features(m)
ok_bar = valid(m, f) & E.ok & (m.tod.values >= 65) & (m.tod.values <= 22 * 60 + 29) & ~m.last_of_session.values
onset = lambda s0: np.where(np.r_[0, s0[:-1]] == s0, 0, s0)
S = {'P1 run4 4A onset': onset(sig_run(f, 4, 4)), 'P2 RSI3&z60': both(sig_rsi(f, 3, 97.5), sig_z(f, 60, 2))}
o, c = m.open.values, m.close.values; spr = E.H._spr['base']
for k, s in S.items():
    s = np.where(ok_bar, s, 0)
    for per, sel in (('TRAIN', E.train), ('TEST', ~E.train)):
        i = np.where((s != 0) & sel)[0]; i = i[i < len(c) - 6]; d = s[i]
        parts = [(o[i + 1] - c[i]) * d, (c[i + 1] - o[i + 1]) * d, (c[i + 2] - c[i + 1]) * d, (c[i + 3] - c[i + 2]) * d, (c[i + 5] - c[i + 3]) * d]
        print(f'{k:18s} {per:5s} n {len(i):4d}  gap {parts[0].mean():+.3f}  bar+1 {parts[1].mean():+.3f}  bar+2 {parts[2].mean():+.3f}  '
              f'bar+3 {parts[3].mean():+.3f}  bars+4..5 {parts[4].mean():+.3f}  | spread paid {spr[i + 1].mean():.3f}  mean A {f.A.values[i].mean():.2f}')
