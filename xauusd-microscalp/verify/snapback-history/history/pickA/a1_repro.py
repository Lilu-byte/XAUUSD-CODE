"""Step 1: reproduce pick A on M15 independently, cross-check the engine with a plain loop, baselines,
cost / fill / latency variants, quarters, truncation test."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickA')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-history')
from alib import *
import hlib

def tsel(T, lo, hi):
    m = np.ones(len(T), bool)
    if lo: m &= (T.entry >= pd.Timestamp(lo)).values
    if hi: m &= (T.entry < pd.Timestamp(hi)).values
    return m


d = finish(read('M15')); f = features(d, 15)
s = signal(d, f, 4.0, True)
hd = hlib.load_tf('M15'); hf = hlib.features(hd, 'M15'); hs = hlib.signal(hd, hf, 2, 4.0, 1)
print('spread_usd identical to hlib:', np.allclose(d.spread_usd.values, hd.spread_usd.values),
      '| signal bars mine', int((s != 0).sum()), 'colleague', int((hs != 0).sum()), 'mismatches', int((s != hs).sum()))
E = Eng(d, 15)
days, T = E.run(s, 4, 25, 3)
L = sim_loop(d, s, 4, 25, 3, E.entry_ok)
m = T.merge(L, on='ei', how='outer', suffixes=('', '_l'), indicator=True)
print('engine vs plain loop: trades', len(T), len(L), 'unmatched', int((m._merge != 'both').sum()),
      'max |pnl diff|', float((m.pnl - m.pnl_l).abs().max()), 'exit-bar mismatches', int((m.xi != m.xi_l).sum()))
P = {'TRAIN': ('2022-07-01', '2025-01-01'), 'TEST': ('2025-01-01', None), 'TEST_PRE_M1': ('2025-01-01', '2026-06-26'),
     'M1ERA': ('2026-06-26', None), 'ALL': (None, None)}
runs = {'base': (days, T), 'bar': E.run(s, 4, 25, 3, spread='bar'), 'wide': E.run(s, 4, 25, 3, spread='wide'),
        'ohlc': E.run(s, 4, 25, 3, fill='OHLC'), 'stop': E.run(s, 4, 25, 3, fill='STOP'),
        'lat1': E.run(s, 4, 25, 3, latency=1),
        'along': E.run(np.where(s != 0, 1., 0.), 4, 25, 3), 'ashort': E.run(np.where(s != 0, -1., 0.), 4, 25, 3)}
NS = 100
R = [E.run(rand_dirs(s, z), 4, 25, 3) for z in range(NS)]
for p, (lo, hi) in P.items():
    st = stats(days, T, lo, hi)
    v = {k: stats(*runs[k], lo, hi)['per_day'] for k in runs if k != 'base'}
    v['comm'] = stats(days, T, lo, hi, extra=COMM)['per_day']
    rp = np.array([stats(a, b, lo, hi)['per_day'] for a, b in R])
    tt = T[tsel(T, lo, hi)]
    print(f'{p:11s}', fmt(st))
    print(f'{"":11s} bar {v["bar"]:+.2f} wide {v["wide"]:+.2f} comm {v["comm"]:+.2f} ohlc {v["ohlc"]:+.2f} stop {v["stop"]:+.2f} '
          f'lat1 {v["lat1"]:+.2f} | always-long {v["along"]:+.2f} always-short {v["ashort"]:+.2f} | random({NS}) mean {rp.mean():+.2f} '
          f'sd {rp.std():.2f} share>=pick {(rp >= st["per_day"]).mean():.2f} | long/tr {tt.pnl[tt.dir == 1].mean():+.2f} '
          f'short/tr {tt.pnl[tt.dir == -1].mean():+.2f} stops hit {int((tt.pnl <= -24.5).sum())}')
# quarters
q = days.pnl.groupby(days.index.to_period('Q')).mean()
qn = T.groupby(T.entry.dt.to_period('Q')).pnl.agg(['size', 'mean', 'sum'])
qw = runs['wide'][0].pnl.groupby(days.index.to_period('Q')).mean()
qc = (days.pnl - COMM * days.trades).groupby(days.index.to_period('Q')).mean()
qr = pd.concat([a.pnl for a, _ in R], axis=1).mean(axis=1).groupby(days.index.to_period('Q')).mean()
ql = runs['along'][0].pnl.groupby(days.index.to_period('Q')).mean()
print('\nquarters: $/day base (wide | comm) [trades, $/tr] random-mean always-long')
print('  ' + '; '.join(f"{i} {q[i]:+.2f} ({qw[i]:+.2f}|{qc[i]:+.2f}) [{int(qn['size'].get(i, 0))},{qn['mean'].get(i, np.nan):+.2f}] r{qr[i]:+.2f} L{ql[i]:+.2f}" for i in q.index))
print('  positive quarters', int((q > 0).sum()), '/', len(q))
# concentration
tp = T.sort_values('pnl', ascending=False)
for p, (lo, hi) in P.items():
    if p == 'ALL': continue
    tt = T[tsel(T, lo, hi)].pnl.sort_values(ascending=False)
    print(f'{p}: total {tt.sum():+.1f}; without best 5 trades {tt.iloc[5:].sum():+.1f}; without best 10 {tt.iloc[10:].sum():+.1f}; '
          f'median trade {tt.median():+.2f}')
# bootstrap of trade means (TEST) and the sign test
rng = np.random.default_rng(0)
for p in ('TRAIN', 'TEST'):
    lo, hi = P[p]; tt = T[tsel(T, lo, hi)].pnl.values
    bs = np.array([rng.choice(tt, len(tt)).mean() for _ in range(5000)])
    print(f'{p} bootstrap $/trade 90% CI [{np.quantile(bs, .05):+.2f}, {np.quantile(bs, .95):+.2f}], P(mean<=0) {np.mean(bs <= 0):.3f}')
T.to_csv('/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickA/pickA_trades_M15.csv', index=False)
# truncation test
rng = np.random.default_rng(11); bad = 0; tot = 0
idx = np.r_[rng.integers(100, len(d) - 1, 300), np.where(s != 0)[0][rng.integers(0, int((s != 0).sum()), 100)]]
for i in idx:
    dc = d.iloc[:i + 1]; fc = features(dc, 15); sc = signal(dc, fc, 4.0, True)
    tot += 1; bad += int(sc[i] != s[i])
print(f'truncation test: {tot} bars (100 of them signal bars), {bad} mismatches')
