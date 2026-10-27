"""Checks: (1) _simx with one leg and no BE/trail == ea/ea_sim._sim_next (after the EA filter), several configs, all
fills and spreads; (2) _simlad with lad_max=1 == _simx one leg max_open 1; (3) a hand check of one time-exit trade."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from sb import *
from ea_sim import _sim_next

m, H = load_train()
f = feats(m)
sigs = {'r3>3a': fade_signal(f, 3, 'atr', 3.0), 'r1>6$away': fade_signal(f, 1, 'usd', 3.0, 'away'),
        'coin': random_like(np.ones(len(m)), 7)}
bad = 0; nchk = 0
for name, s in sigs.items():
    for tp, sl, to, mo, cd in ((1000, 10, 5, 1, 0), (0.5, 5, 5, 1, 0), (3, 20, 10, 3, 2), (1, 3, 2, 5, 0)):
        for fill in ('FAIR', 'OHLC', 'STOP'):
            for sp in ('base', 'bar', 'wide'):
                sf = ea_filter(m, s)
                a = _sim_next(H.o, H.h, H.l, H.c, H._spr[sp], H.tod, H.day, H.last, sf, float(tp), float(sl), int(to), int(mo),
                              FILL[fill], 0.0, 0.0, int(cd))
                d, t = H.run_x(s, (tp,), sl, to, mo, cd, fill=fill, spread=sp)
                ok = np.allclose(a[0], d.pnl.values) and len(a[2]) == len(t) and np.array_equal(a[2], t.ei.values) \
                    and np.allclose(a[4], t.pnl.values)
                nchk += 1; bad += (not ok)
print(f'_simx vs _sim_next: {nchk} configs, {bad} mismatches')
bad = 0; nchk = 0
for name, s in sigs.items():
    for tp, sl, to in ((0.5, 5, 5), (1.0, 10, 3), (0.25, 3, 10)):
        for fill in ('FAIR', 'OHLC', 'STOP'):
            d1, t1 = H.run_x(s, (tp,), sl, to, 1, 0, fill=fill)
            d2, t2 = H.run_lad(s, f.p3.values, tp, sl, to, lad_max=1, fill=fill)
            ok = np.allclose(d1.pnl.values, d2.pnl.values) and np.array_equal(t1.ei.values, t2.ei.values)
            nchk += 1; bad += (not ok)
print(f'_simlad(lad_max=1) vs _simx: {nchk} configs, {bad} mismatches')
# hand check: first time-exit long and short trade
s = sigs['r3>3a']
d, t = H.run_x(s, (1000,), 50, 5, 1, 0)
sp = H._spr['base']
for dirn in (1, -1):
    r = t[(t.dir == dirn) & (t.kind == 3)].iloc[0]; i = int(r.ei); x = int(r.xi)
    exp = (H.c[x] - (H.o[i + 1] + sp[i + 1])) if dirn == 1 else (H.o[i + 1] - (H.c[x] + sp[x]))
    print(f'hand check dir {dirn:+d}: entry bar {m.index[i]}, exit bar {m.index[x]} ({x - i} bars), sim {r.pnl:+.4f} hand {exp:+.4f}')
# legs: 3 legs == sum of three one-leg runs when signals never overlap (spot check on totals with max_open 3, cooldown huge)
d3, t3 = H.run_x(s, (0.25, 0.5, 1.0), 10, 5, 3, 0)
print('3-leg run: positions', len(t3), 'legs share', t3.leg.value_counts(normalize=True).round(3).to_dict())
# synthetic check of the ladder's mode-1 chain (see the hand calculation in the comment)
n = 30
o = np.full(n, 103.4); h = o + 0.05; l = o - 0.05; c = o.copy()
o[:11] = h[:11] = l[:11] = c[:11] = 100.0
o[11], h[11], l[11], c[11] = 100.0, 100.9, 99.9, 100.8      # rung 1 (entry 100.1) TP 100.6 -> re-enter 100.7, TP 101.2 not reached
o[12], h[12], l[12], c[12] = 100.8, 101.5, 100.7, 101.4     # rung 2 TP 101.2 -> rung 3 at 101.3 (TP 101.8) carried
o[13], h[13], l[13], c[13] = 101.4, 103.5, 101.3, 103.4     # rung 3 TP 101.8 -> rungs 4 (TP 102.4) and 5 (TP 103.0) fill in-bar, rung 6 at 103.1 carried
spr = np.full(n, 0.1); raw = np.full(n, 0.05); tod = 600 + np.arange(n); day = np.zeros(n, np.int64)
last = np.zeros(n, np.bool_); last[-1] = True
sig = np.zeros(n, np.int64); sig[10] = 1; lvl = np.full(n, 105.0)
from sb import _simlad
dp, dt, ti, to, pn, dr, rg, kd = _simlad(o, h, l, c, spr, raw, tod, day, last, sig, lvl, 0.5, 5.0, 5, 10, 1.0, 30, 1, 1)
print('synthetic ladder: pnl per rung', np.round(pn, 3).tolist(), 'rungs', rg.tolist(), 'total %.2f (hand: 5 x 0.5 + 0.3 = 2.80)' % dp.sum())
