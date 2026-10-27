"""Real-data checks: coin-flip entries, spread paid vs loss per trade; day-boundary exits; data quirks."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
import mlib

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
m1 = mlib.load_m1()
H = mlib.Harness(m1)
n = len(m1)
print('first/last close', m1.close.iloc[0], m1.close.iloc[-1], 'drift per minute', (m1.close.iloc[-1] - m1.close.iloc[0]) / n)

# per-trade spread paid: long -> entry-bar spread; short -> exit-bar spread
def spread_paid(tr, spr):
    ii = m1.index.get_indexer(tr.entry)
    io = ii + tr.bars.values
    return np.where(tr.dir.values == 1, spr[ii], spr[io]), ii, io

rows = []
for seed in (1, 2):
    rng = np.random.default_rng(seed)
    sig = np.where(rng.random(n) < .5, 1, -1)
    for tp, sl, to in [(0.3, 0.3, 5), (0.5, 0.5, 10), (1.0, 0.5, 10), (0.5, 1.0, 10), (1.0, 1.0, 15), (0.3, 1.0, 10), (2.0, 2.0, 30)]:
        for sp in ('bar', 'base', 'wide'):
            r = dict(seed=seed, tp=tp, sl=sl, to=to, spread=sp)
            for fm in ('FAIR', 'OHLC', 'STOP'):
                d, tr = H.run(sig, tp, sl, timeout=to, fill=fm, spread=sp)
                r[fm] = tr.pnl.mean()
                if fm == 'FAIR':
                    paid, ii, io = spread_paid(tr, H._spr[sp])
                    r['n'] = len(tr); r['paid'] = paid.mean(); r['FAIR+paid'] = tr.pnl.mean() + paid.mean()
                    r['se'] = tr.pnl.std() / np.sqrt(len(tr))
                    r['long'] = tr.pnl[tr.dir == 1].mean(); r['short'] = tr.pnl[tr.dir == -1].mean()
                    xd = H.day[io] != H.day[ii]
                    r['overnight_n'] = int(xd.sum()); r['overnight_pnl_sum'] = tr.pnl[xd].sum()
                    r['overnight_absmean'] = tr.pnl[xd].abs().mean() if xd.any() else np.nan
            rows.append(r)
res = pd.DataFrame(rows)
print(res.round(4).to_string())
res.to_csv('/mnt/project-files/xauusd-microscalp/audit/real_coinflip.csv', index=False)

# bar-boundary gap: o[i+1] - c[i]
gap = m1.open.values[1:] - m1.close.values[:-1]
same = H.day[1:] == H.day[:-1]
g = gap[same]
print('\nintra-day open-vs-prev-close gap: mean %.4f  mean|gap| %.4f  frac nonzero %.3f' % (g.mean(), np.abs(g).mean(), (g != 0).mean()))
body = (m1.close - m1.open).values[:-1][same]
print('E[gap * sign(body of bar i)] = %.4f  (positive = continuation in the bar direction)' % (np.sign(body) * g).mean())
pos_in_range = ((m1.close - m1.low) / (m1.high - m1.low).replace(0, np.nan)).values[:-1][same]
for lo, hi in ((0, .1), (.1, .5), (.5, .9), (.9, 1.01)):
    mk = (pos_in_range >= lo) & (pos_in_range < hi)
    print(f'  close position in range [{lo},{hi}): mean gap {g[mk].mean():+.4f}  n={mk.sum()}')

# zero-spread bars and their effect
z = m1.spread.values == 0
print('\nzero-spread bars: %d (%.1f%%), all before %s; TRAIN share %.1f%%' % (
    z.sum(), 100 * z.mean(), m1.index[z].max(), 100 * z[m1.index < mlib.SPLIT].mean()))
for per, sel in (('train', m1.index < mlib.SPLIT), ('test', m1.index >= mlib.SPLIT)):
    print(f'  {per}: mean base spread {H._spr["base"][sel].mean():.4f}  mean bar spread {H._spr["bar"][sel].mean():.4f}')
print('  base spread, Jun26-Jul08 vs rest of TRAIN: %.4f vs %.4f' % (
    H._spr['base'][m1.index < '2026-07-09'].mean(), H._spr['base'][(m1.index >= '2026-07-09') & (m1.index < mlib.SPLIT)].mean()))
print('mean bar spread by hour ($):', (m1.spread_usd.groupby(m1.index.hour).mean()).round(3).to_dict())

# float ties at TP level: how often the bid high equals the long TP level to the cent
for tp in (0.1, 0.3, 0.5):
    e = m1.close.values[:-1] + H._spr['base'][:-1]
    tpp = e + tp
    hh = m1.high.values[1:]
    tie = np.abs(hh - tpp) < 1e-6
    print(f'TP {tp}: next-bar high equals long TP level (to the cent) in {tie.mean() * 100:.2f}% of bars; '
          f'of those, harness counts hit (h>=tpp) {(hh[tie] >= tpp[tie]).mean() * 100:.1f}%')
