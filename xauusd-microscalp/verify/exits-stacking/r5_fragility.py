"""Step 4d: fragility of the zero-failure result on the REAL M1 data: tiny perturbations of spread, path seed, and
signal timing (a few missed signals, 1-bar latency). A failure = basket force-closed at the session end with a loss."""
from common import *

m1, H, g = load_m1_harness()
SPLIT = mlib.SPLIT
mr = mr_signal(m1)
pd.set_option('display.width', 250)
rows = []


def rec(label, sig=mr, seeds=range(5), **kw):
    for s in seeds:
        out = g.run(sig, seed=s, **kw)
        b = out[1]
        for per, lo, hi in (('TRAIN', None, SPLIT), ('TEST', SPLIT, None)):
            r = summ(g, *out, lo=lo, hi=hi); r.update(label=label, seed=s, period=per)
            rows.append(r)


def show(label):
    R = pd.DataFrame([r for r in rows if r['label'] == label])
    out = []
    for per in ('TRAIN', 'TEST'):
        q = R[R.period == per]
        out.append(f'{per} per_day {q.per_day.mean():+7.2f} [{q.per_day.min():+7.2f},{q.per_day.max():+6.2f}] fail-runs {(q.n_forced > 0).mean():.2f} '
                   f'worst_day {q.worst_day.min():+7.0f}')
    print(f'{label:34s} ' + ' | '.join(out))


rec('base, path seeds 0-49', seeds=range(50)); show('base, path seeds 0-49')
for x in (-0.03, -0.02, -0.01, 0.01, 0.02, 0.03, 0.05):
    lab = f'spread base{x:+.2f}'; rec(lab, spr=g.spr['base'] + x); show(lab)
for w in (0.20, 0.25, 0.28, 0.30, 0.32, 0.35):
    lab = f'flat spread {w:.2f}'; rec(lab, spr=np.full(len(m1), w)); show(lab)
rng = np.random.default_rng(5)
for drop in (0.01, 0.02, 0.05):
    for rep in range(5):
        keep = rng.random(len(mr)) >= drop
        lab = f'drop {drop:.0%} of signals'; rec(lab, sig=np.where(keep, mr, 0), seeds=[rep])
    show(lab)
lat = np.r_[0, mr[:-1]]          # act one bar later (signal of bar i-1 executed at close of bar i)
rec('1-bar latency', sig=lat); show('1-bar latency')
for ps in ('OHLC', 'ADV', 'FAV'):
    rec(f'path {ps}', path=ps, seeds=[0]); show(f'path {ps}')
R = pd.DataFrame(rows); R.to_csv(VOUT + 'r5_fragility.csv', index=False)

# which days fail under the flat 0.30 spread (the colleague's 'wide' model) on TRAIN
for s in range(3):
    d, b, e, lv = g.run(mr, seed=s, spread='wide')
    f = b[b.pnl < 0]
    print(f'wide seed {s}: failures {[(str(t), lev, round(p, 1)) for t, lev, p in zip(f.start, f.levels, f.pnl)]}')
