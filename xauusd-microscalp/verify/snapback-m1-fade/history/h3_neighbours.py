"""Lens (2): multiple testing. (a) How many configurations the family scored and where P1 ranks (from the colleague's
own TRAIN result files). (b) P1's one-step neighbours on TRAIN (and its halves) and TEST. (c) A local grid
(threshold x hold x max_open) on TRAIN and TEST to see whether TEST money is a plateau or a spike.
Diagnostics only: nothing here is selected or proposed as a new pick."""
import sys, glob
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history')
from vlib import *

FAM = '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade/'
pd.set_option('display.width', 250)
# ---------------------------------------------------------------- (a) counts and rank
s1 = pd.read_csv(FAM + 's1_edge_train.csv'); s2 = pd.read_csv(FAM + 's2_scan_train.csv.gz')
s2b = pd.read_csv(FAM + 's2b_refine_train.csv.gz'); s3 = pd.read_csv(FAM + 's3_tp1_train.csv.gz')
n_hist = 32
print(f'configurations scored by the family: stage1 fill-free cells {len(s1)}, stage2 {len(s2)}, stage2b {len(s2b)}, '
      f'stage3 {len(s3)}, history analogs {n_hist}; simulated total (2+2b+3+hist) {len(s2) + len(s2b) + len(s3) + n_hist}, '
      f'plus {len(s1)} fill-free cells')
for nm, R in (('stage2', s2), ('stage2b', s2b)):
    R = R.copy(); R['minh'] = R[['pd_A', 'pd_B']].min(axis=1)
    p = R[(R.k == 3) & (R['mode'] == 'usd') & (R.th == 7.0) & (R.gate == 'none') & (~R.fresh) & (R.sgate == 0) & (R.N == 3)
          & (R.sl == 10.0) & (R.get('mo') == 2) & ((R.tp == 1000.0) if 'tp' in R else True)]
    if 'be_trig' in R: p = p[(p.be_trig == 0) & (p.trail == 0)]
    if len(p):
        r = p.iloc[0]
        print(f'{nm}: P1 TRAIN {r.pd_tr:+.2f}/day, min-half {r.minh:+.2f}; rank by TRAIN $/day {int((R.pd_tr > r.pd_tr).sum()) + 1} of {len(R)}, '
              f'by min-half {int((R.minh > r.minh).sum()) + 1} of {len(R)}; share of configs with both halves > 0: {(R.minh > 0).mean():.3f}; '
              f'configs with TRAIN >= +$5/day: {(R.pd_tr >= 5).sum()}')
    else:
        print(f'{nm}: P1 cell not on this grid (th 7 / mo 2 only in stage 2b)')
sn = s2b[s2b.region == 'snap'].copy(); sn['minh'] = sn[['pd_A', 'pd_B']].min(axis=1)
r = sn[(sn.th == 7.0) & (sn['mode'] == 'usd') & (~sn.fresh) & (sn.sgate == 0) & (sn.N == 3) & (sn.sl == 10) & (sn.tp == 1000) & (sn.mo == 2) & (sn.be_trig == 0) & (sn.trail == 0)].iloc[0]
print(f'stage2b snap region only ({len(sn)} configs): P1 rank by TRAIN $/day {int((sn.pd_tr > r.pd_tr).sum()) + 1}, by min-half {int((sn.minh > r.minh).sum()) + 1}; '
      f'median config {sn.pd_tr.median():+.2f}/day; 99th pct {sn.pd_tr.quantile(.99):+.2f}')

# ---------------------------------------------------------------- (b) one-step neighbours
m = load_m1(); A = Arr(m)
c = m.close


def sig(k=3, th=7.0, fresh=False, sgate=0.0, atr_mult=None):
    r = (c - c.shift(k)).values
    lim = th if atr_mult is None else atr_mult * (m.high - m.low).rolling(240).mean().values
    s = np.where(np.abs(r) > lim, -np.sign(r), 0.0)
    if fresh:
        prev = np.r_[0.0, s[:-1]]; s = np.where(prev == s, 0.0, s)
    if sgate > 0:
        s = np.where(m.spread_usd.values <= sgate + 1e-9, s, 0.0)
    return np.nan_to_num(s)


def row(name, s, **kw):
    d, t = run(A, s, **kw)
    a = summ(d, t, None, HALF); b = summ(d, t, HALF, SPLIT); tr = summ(d, t, None, SPLIT); te = summ(d, t, SPLIT, None)
    return dict(name=name, train=tr['per_day'], A=a['per_day'], B=b['per_day'], test=te['per_day'], test_tr=te['trades_day'],
                test_pt=te['per_trade'], train_pt=tr['per_trade'])


base = dict(k=3, th=7.0)
rows = [row('P1 (k3, $7, hold 3, max 2, SL 10)', sig())]
for th in (6.0, 8.0): rows.append(row(f'threshold ${th:g}', sig(th=th)))
for k in (2, 4): rows.append(row(f'lookback {k} bars', sig(k=k)))
for N in (2, 4): rows.append(row(f'hold {N} bars', sig(), timeout=N))
for sl in (8.0, 15.0): rows.append(row(f'stop ${sl:g}', sig(), sl=sl))
for mo in (1, 3): rows.append(row(f'max open {mo}', sig(), max_open=mo))
rows.append(row('fresh (first bar of a run only)', sig(fresh=True)))
rows.append(row('signal-bar spread <= $0.15', sig(sgate=0.15)))
rows.append(row('TP $6 instead of none', sig(), tp=6.0))
rows.append(row('cooldown 3 bars', sig(), cooldown=3))
rows.append(row('threshold 3.5 x ATR240 (ATR version)', sig(atr_mult=3.5)))
N = pd.DataFrame(rows)
print('\n(b) one-step neighbours ($/day):')
print(N.round(2).to_string(index=False))
nb = N.iloc[1:13]
print(f'one-step neighbours (12): TRAIN > 0: {(nb.train > 0).sum()}, both TRAIN halves > 0: {((nb.A > 0) & (nb.B > 0)).sum()}, '
      f'TEST > 0: {(nb.test > 0).sum()}, TEST >= +5/day: {(nb.test >= 5).sum()}; median TRAIN {nb.train.median():+.2f}, median TEST {nb.test.median():+.2f}')
N.to_csv(OUT + 'h3_neighbours.csv', index=False)

# ---------------------------------------------------------------- (c) local grid
G = []
for th in (5.0, 6.0, 7.0, 8.0, 9.0, 10.0):
    s = sig(th=th)
    for Nh in (1, 2, 3, 4, 5, 6):
        for mo in (1, 2, 3):
            r = row(f'th{th:g} N{Nh} mo{mo}', s, timeout=Nh, max_open=mo); r.update(th=th, N=Nh, mo=mo); G.append(r)
G = pd.DataFrame(G); G.to_csv(OUT + 'h3_local_grid.csv', index=False)
print(f'\n(c) local grid threshold $5-10 x hold 1-6 x max open 1-3 = {len(G)} configs (diagnostic)')
print(f'  TRAIN > 0: {(G.train > 0).mean():.2f}; TEST > 0: {(G.test > 0).mean():.2f}; TEST >= 5: {(G.test >= 5).mean():.2f}; '
      f'corr(TRAIN, TEST) across the grid {G.train.corr(G.test):+.2f}; rank corr {G.train.rank().corr(G.test.rank()):+.2f}')
for col in ('th', 'N', 'mo'):
    print('  mean by ' + col + ': ' + ' '.join(f'{k:g}: TRAIN {v.train:+.2f} TEST {v.test:+.2f} |' for k, v in G.groupby(col)[['train', 'test']].mean().iterrows()))
pv = G[G.mo == 2].pivot(index='th', columns='N', values='test')
pt = G[G.mo == 2].pivot(index='th', columns='N', values='train')
print('  max open 2, TRAIN $/day (rows threshold, cols hold):'); print(pt.round(1).to_string())
print('  max open 2, TEST $/day:'); print(pv.round(1).to_string())
best = G.sort_values('train', ascending=False).head(5)
print('  top 5 of this grid by TRAIN and their TEST: ' + '; '.join(f'{r.name}: {r.train:+.2f} -> {r.test:+.2f}' for r in best.itertuples()))
