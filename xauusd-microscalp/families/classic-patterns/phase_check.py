"""TRAIN only: is the pullback-fade edge specific to the clock-aligned phase? Edge per phase of k-min candles."""
from sigs import *
H = Harness(); m = H.m1
ok = m.tod.values < END_TOD - 15
A = ok & (m.index < pd.Timestamp('2026-08-01')); B = ok & (m.index >= pd.Timestamp('2026-08-01')) & (m.index < SPLIT)
spr = spread_series(m, 'base'); HZ = (1, 2, 3, 5, 10)
FWD = {k: (m.close.shift(-k) - m.close).values for k in HZ}
nd = {'A': len(np.unique(m.index[A].date)), 'B': len(np.unique(m.index[B].date))}
mm_ = m.index.minute.values
for k in (2, 3):
    for q, htf in ((1.0, 'H1'), (2.0, 'H1'), (2.0, 'M15')):
        s = pullback(m, k, True, q, 0.9, htf)
        for p in range(k):
            sp = np.where(mm_ % k == (p + k - 1) % k, s, 0)   # rows completing phase-p candles
            out = []
            for lab, msk in (('A', A), ('B', B)):
                g = msk & (sp != 0)
                out.append(f"{lab} n/d={g.sum()/nd[lab]:5.1f} " + ' '.join(f"{np.nanmean(FWD[h][g]*sp[g]-spr[g]):+.2f}" for h in HZ))
            print(f'k={k} q={q} {htf} phase={p}: ' + ' | '.join(out))
# minute-of-hour profile of the M2 q1 H1 fixed signal edge (net5) in train
s = pullback(m, 2, False, 1.0, 0.9, 'H1'); g = (A | B) & (s != 0)
f = FWD[5] * s - spr
dfm = pd.DataFrame({'min': mm_[g] // 10 * 10, 'hour': m.index.hour.values[g], 'net5': f[g]})
print(dfm.groupby('min').net5.agg(['mean', 'count']).round(2).T)
print(dfm.groupby('hour').net5.agg(['mean', 'count']).round(2).T)
