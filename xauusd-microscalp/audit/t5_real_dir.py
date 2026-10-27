"""Real data: residual (pnl + spread paid) by direction; wick asymmetry; overnight carry; long/short spread timing."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
import mlib

m1 = mlib.load_m1(); H = mlib.Harness(m1); n = len(m1)
rng = np.random.default_rng(11)
rows = []
for tp, sl, to in [(0.3, 0.3, 5), (0.5, 0.5, 10), (1.0, 0.5, 10), (0.5, 1.0, 10), (1.0, 0.3, 10), (0.3, 1.0, 10), (1.0, 1.0, 15)]:
    for sp in ('base', 'wide'):
        for seed in range(4):
            sig = np.where(np.random.default_rng(100 + seed).random(n) < .5, 1, -1)
            d, tr = H.run(sig, tp, sl, timeout=to, fill='FAIR', spread=sp)
            ii = m1.index.get_indexer(tr.entry); io = ii + tr.bars.values
            spr = H._spr[sp]
            paid = np.where(tr.dir == 1, spr[ii], spr[io])
            same_day = H.day[io] == H.day[ii]
            res = tr.pnl.values + paid
            for dname, dv in (('long', 1), ('short', -1)):
                mk = (tr.dir.values == dv) & same_day
                rows.append(dict(tp=tp, sl=sl, to=to, spread=sp, seed=seed, dir=dname, n=mk.sum(), resid=res[mk].mean(),
                                 se=res[mk].std() / np.sqrt(mk.sum())))
r = pd.DataFrame(rows)
g = r.groupby(['tp', 'sl', 'to', 'spread', 'dir']).agg(resid=('resid', 'mean'), se=('se', lambda s: np.sqrt((s ** 2).mean() / len(s))), n=('n', 'mean'))
pd.set_option('display.width', 200)
print('residual = pnl + spread paid (should be ~0 on a driftless market), same-day trades only, 4 seeds')
print(g.round(4).unstack('dir').to_string())

# wick asymmetry (bid candles): spread-widening shows up as downward bid spikes
up = (m1.high - m1[['open', 'close']].max(axis=1)); dn = (m1[['open', 'close']].min(axis=1) - m1.low)
print('\nmean upper wick %.4f  mean lower wick %.4f  (ratio %.3f)' % (up.mean(), dn.mean(), dn.mean() / up.mean()))
for q in (.9, .99, .999):
    print(f'  q{q}: upper {up.quantile(q):.3f}  lower {dn.quantile(q):.3f}')
print('mean (high-open) %.4f  mean (open-low) %.4f' % ((m1.high - m1.open).mean(), (m1.open - m1.low).mean()))
for per, sel in (('train', m1.index < mlib.SPLIT), ('test', m1.index >= mlib.SPLIT)):
    print(f'  {per}: (open-low)-(high-open) = {((m1.open - m1.low) - (m1.high - m1.open))[sel].mean():+.4f}; '
          f'net drift/bar {(m1.close - m1.open)[sel].mean():+.4f}')

# overnight / weekend gaps: first open of a day vs last close of previous day
first = np.r_[True, H.day[1:] != H.day[:-1]]
idx = np.where(first)[0][1:]
gap = m1.open.values[idx] - m1.close.values[idx - 1]
dt = (m1.index[idx] - m1.index[idx - 1]).total_seconds() / 3600
print('\nsession-break gaps: n=%d, mean|gap| %.2f, median|gap| %.2f, max|gap| %.2f; hours between bars: %s' % (
    len(gap), np.abs(gap).mean(), np.median(np.abs(gap)), np.abs(gap).max(), pd.Series(dt.round(2)).value_counts().to_dict()))
# compare with a normal 2-hour intraday move
c = m1.close
mv = (c.shift(-120) - c)[m1.tod.between(9 * 60, 20 * 60)].abs().mean()
print('typical intraday |2h move| %.2f' % mv)
print('last bar time of each day:', pd.Series(m1.index[np.r_[H.day[1:] != H.day[:-1], True]].strftime('%H:%M')).value_counts().to_dict())
