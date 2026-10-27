"""Train-only neighbourhood of the train pick (Donchian 120/60 both ways + D1 SMA regime): SMA length and
whether to also close on a regime flip. Plus a cost check (spread x2). No test numbers."""
from rules import *
a, b = TRAIN
d, sig0, kw0 = candidate('donchian')
D = load('D1')
out = []
for n in [150, 200, 250]:
    up = htf(d, 'D1', (D.close > sma(D.close, n)).astype(float).values) > 0.5
    for flip in [False, True]:
        sig = np.asarray(sig0, float).copy(); kw = dict(kw0)
        sig[(sig > 0) & ~up] = 0; sig[(sig < 0) & up] = 0
        if flip:
            kw['exit_long'] = np.asarray(kw['exit_long'], bool) | ~up
            kw['exit_short'] = np.asarray(kw['exit_short'], bool) | up
        for cost in [1, 2]:
            t = simulate(d, sig, spread=0.30 * cost, slip=0.10 * cost, **kw)
            tt, dd = window(t, d, a, b); tt = tt[tt.entry_time >= a]; p = daily(tt, dd)
            yr = p.groupby(p.index.year).mean().round(2).to_dict()
            out.append(dict(sma=n, flip_exit=flip, cost=cost, per_day=round(p.mean(), 3), trades=len(tt), dd=round(maxdd(p)), **{f'y{k}': v for k, v in yr.items()}))
r = pd.DataFrame(out); pd.set_option('display.width', 200)
print(r.to_string(index=False))
