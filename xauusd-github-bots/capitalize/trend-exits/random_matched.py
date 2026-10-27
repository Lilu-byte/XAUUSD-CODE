"""Exposure-matched random benchmark: random long entry bars while the D1 regime is on, thinned so the number of
trades (and time in market) matches the real breakout signal; same exits. 40 runs. Test window and full data."""
from common import *
d = load('H1'); a = atr(d, 14); reg = d1_regime(d, 200); sig = np.where(reg, dc_sig(d, 120), 0.0)
cand = np.flatnonzero(reg); ALL = ('2016-07-29', '2026-10-10')
for nm, kw in (('pick (pyramid)', dict(sl=2 * a, trail_m=4.0, add_trig=2.0, max_units=2)), ('no pyramid', dict(sl=2 * a, trail_m=4.0))):
    real = tx.tsim(d, sig, a, **kw); n_real = int((real.unit == 1).sum())
    expo = lambda t: (t[t.unit == 1].xi - t[t.unit == 1].ei).sum() / len(d)
    rng = np.random.default_rng(11); res = []
    k = 420   # random signal bars, calibrated so the random runs average about the same trade count as the real rule
    for _ in range(40):
        s = np.zeros(len(d)); s[rng.choice(cand, k, replace=False)] = 1.0
        t = tx.tsim(d, s, a, **kw)
        res.append((int((t.unit == 1).sum()), expo(t), tx.summary(t, d, *TEST)['per_day'], tx.summary(t, d, *ALL)['per_day'], tx.summary(t, d, *TRAIN)['per_day']))
    r = np.array(res)
    rt, ra, rtr = tx.summary(real, d, *TEST)['per_day'], tx.summary(real, d, *ALL)['per_day'], tx.summary(real, d, *TRAIN)['per_day']
    print(f'== {nm}: real trades {n_real}, exposure {expo(real):.3f}, train {rtr}, test {rt}, all {ra}')
    print(f'   random: trades {r[:,0].mean():.0f}, exposure {r[:,1].mean():.3f}, train median {np.median(r[:,4]):.2f} (real beats {100*(r[:,4]<rtr).mean():.0f}%), '
          f'test median {np.median(r[:,2]):.2f} (real beats {100*(r[:,2]<rt).mean():.0f}%), all median {np.median(r[:,3]):.2f} (real beats {100*(r[:,3]<ra).mean():.0f}%)')
