"""Random benchmarks on the TEST window (2022-01..2026-10) and full data for the frozen pick:
(a) coin-flip direction on the same entry bars, same exits (shorts use the mirrored chandelier);
(b) long-only entries at random H1 bars while the D1 regime is on, same count as the real signal bars, same exits.
Also: costs doubled."""
from common import *
d = load('H1'); a = atr(d, 14); reg = d1_regime(d, 200); sig = np.where(reg, dc_sig(d, 120), 0.0)
KW = dict(sl=2 * a, trail_m=4.0, add_trig=2.0, max_units=2)
KW0 = dict(sl=2 * a, trail_m=4.0)
def pd_(t, w): return tx.summary(t, d, *w)['per_day']
for nm, kw in (('pick (pyramid)', KW), ('no pyramid', KW0)):
    real = tx.tsim(d, sig, a, **kw)
    rt, ra = pd_(real, TEST), pd_(real, ('2016-07-29', '2026-10-10'))
    cf = [tx.tsim(d, s, a, **kw) for s in tx.coinflip(d, sig, runs=40)]
    cft = np.array([pd_(t, TEST) for t in cf]); cfa = np.array([pd_(t, ('2016-07-29', '2026-10-10')) for t in cf])
    rng = np.random.default_rng(7); n_sig = int((sig == 1).sum()); cand = np.flatnonzero(reg)
    rl = []
    for _ in range(40):
        s = np.zeros(len(d)); s[rng.choice(cand, n_sig, replace=False)] = 1.0
        rl.append(tx.tsim(d, s, a, **kw))
    rlt = np.array([pd_(t, TEST) for t in rl]); rla = np.array([pd_(t, ('2016-07-29', '2026-10-10')) for t in rl])
    print(f'== {nm}: real test {rt} all {ra}')
    print(f'  coin-flip dir: test median {np.median(cft):.2f}, real beats {100*(cft<rt).mean():.0f}% | all median {np.median(cfa):.2f}, beats {100*(cfa<ra).mean():.0f}%')
    print(f'  random long entries in regime: test median {np.median(rlt):.2f} (10-90%: {np.percentile(rlt,10):.2f}..{np.percentile(rlt,90):.2f}), real beats {100*(rlt<rt).mean():.0f}% | all median {np.median(rla):.2f}, beats {100*(rla<ra).mean():.0f}%')
    hc = tx.tsim(d, sig, a, spread=0.60, slip=0.20, **kw)
    print(f'  double costs: test {pd_(hc, TEST)}, all {pd_(hc, ("2016-07-29", "2026-10-10"))}, train {pd_(hc, TRAIN)}')
