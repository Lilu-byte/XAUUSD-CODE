"""Sanity checks for gridsim2 (TRAIN rows / synthetic data only):
1) maxlev=1 grid == single bracket: grid (4-vertex FAIR path) vs run_pw (mlib FAIR) on the same coin-flip signal.
2) Synthetic tick random walk on the first 20 TRAIN days (flat $0.15 spread, K=10000 ticks/bar, mean M1 range ~$1.6):
   bar-path grid vs tick-exact grid on identical prices. Martingale theory: per_position = -spread exactly.
3) Same with an up-drift of +$0.007/min (TRAIN's average): long grids then earn drift x exposure."""
from sigs2 import *
from gridsim2 import *
from synth2 import synth_harness, grid_tick

m1, H = train_harness(); n = len(H.m1)
cf = np.where(np.random.default_rng(5).random(n) < .5, 1, -1)
print('1) single position: grid maxlev=1 vs bracket sim (per trade), real TRAIN, coin flip')
for T, S, to in [(0.3, 0.3, 10), (0.1, 1.0, 10), (1.0, 5.0, 30), (0.5, 20.0, 30)]:
    d, t = run_pw(H, cf, T, S, timeout=to)
    g = [run_grid(H, cf, 1.0, 1, T, S, tmax=to, seed=s) for s in range(3)]
    g4 = run_grid(H, cf, 1.0, 1, T, S, tmax=to, path='BRIDGE', nsub=30)[1].pnl.mean()
    print(f'   tp {T} sl {S} to {to}: bracket FAIR {t.pnl.mean():+.4f} ({len(t)} trades)  grid FAIR4 {np.mean([x[1].pnl.mean() for x in g]):+.4f} '
          f'({np.mean([len(x[1]) for x in g]):.0f} baskets)  grid BRIDGE30 {g4:+.4f}  grid OHLC {run_grid(H, cf, 1.0, 1, T, S, tmax=to, path="OHLC")[1].pnl.mean():+.4f}')

sub = H.m1[H.m1.index < pd.Timestamp('2026-07-25')]
for label, p in (('martingale', 0.5), ('drift +0.007/min', 0.5 + 0.35 / 10000)):
    SH, steps, offs, oc = synth_harness(sub, 10000, p=p, seed=21)
    ns = len(SH.m1)
    print(f'2/3) synthetic {label}: {ns} bars, mean M1 range {(SH.m1.high - SH.m1.low).mean():.2f}, '
          f'net move {SH.c[-1] - SH.o[0]:+.1f}; flat spread 0.15')
    cfs = np.where(np.random.default_rng(7).random(ns) < .5, 1, -1)
    for dn, sig in (('long', np.ones(ns, np.int64)), ('cf', cfs)):
        for step, L, T, S, tm in [(1.0, 10, 0.3, 0, 0), (0.5, 50, 0.1, 0, 0), (2.0, 5, 1.0, 50, 0), (3.0, 20, 0.5, 0, 30), (1.0, 1, 0.3, 5, 30)]:
            bar = [run_grid(SH, sig, step, L, T, S, tmax=tm, spread='bar', seed=s) for s in range(3)]
            b4 = run_grid(SH, sig, step, L, T, S, tmax=tm, spread='bar', path='BRIDGE', nsub=30)[0]
            bpp = np.mean([x[0].pnl.sum() / x[0].positions.sum() for x in bar])
            bpd = np.mean([x[0].pnl.mean() for x in bar]); bw = np.mean([x[0].pnl.min() for x in bar])
            tdp, tpos, tbp = grid_tick(steps, offs, oc, SH._spr['bar'], SH.tod, SH.day, SH.last, sig.astype(np.int64),
                                       step, L, T, S, tm)
            print(f'   {dn:4s} step {step} lev {L:2d} btp {T} bsl {S:2d} tmax {tm:2d}: per_position FAIR4 {bpp:+.3f} BRIDGE30 {b4.pnl.sum() / b4.positions.sum():+.3f} tick {tdp.sum() / tpos.sum():+.3f} | '
                  f'per_day bar {bpd:+7.1f} tick {tdp.mean():+7.1f} | worst day bar {bw:7.1f} tick {tdp.min():7.1f} | '
                  f'basket win bar {np.mean([(x[1].pnl > 0).mean() for x in bar]):.3f} tick {(tbp > 0).mean():.3f}')
    del steps
