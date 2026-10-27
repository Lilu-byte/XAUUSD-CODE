"""(2) random / permutation / always-long-short baselines, (3) cost, fill and latency variants, stop slippage,
(5) concentration: top days, direction, years, quarters; drift decomposition. Prints summaries only."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/repro/pickA')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from vA import *
from mlib import random_like

d = load_m15(); s, ar = sig_A(d); S = Sim(d)
days, T = S.run(s)
P = {'TRAIN': TRAIN, 'TEST': TEST, 'ALL': ('2022-07-01', '2026-10-10')}
base = {k: per(days, T, *v) for k, v in P.items()}
NCONF = 0

def pd_(dd, TT, k, extra=0.0): return per(dd, TT, *P[k], extra=extra)['per_day']

print('=== (2) baselines, $/day: pick TRAIN %+.3f TEST %+.3f ALL %+.3f' % tuple(base[k]['per_day'] for k in P))
R = {k: [] for k in P}
for z in range(50):
    dz, Tz = S.run(random_like(s, z))
    for k in P: R[k].append(pd_(dz, Tz, k))
for k in P:
    r = np.array(R[k])
    print(f"  random 50 seeds {k}: mean {r.mean():+.3f} sd {r.std():.3f} max {r.max():+.3f}; share of seeds >= pick {(r >= base[k]['per_day']).mean():.2f}")
dL, TL = S.run(np.where(s != 0, 1.0, 0.0)); dS, TS = S.run(np.where(s != 0, -1.0, 0.0)); dF, TF = S.run(-s)
for k in P:
    print(f"  {k}: always-long {pd_(dL, TL, k):+.3f}  always-short {pd_(dS, TS, k):+.3f}  flipped (follow the move) {pd_(dF, TF, k):+.3f}  "
          f"pick long share {base[k]['long_share']:.3f}  long $/tr {base[k]['long_pt']:+.2f} (n {base[k]['n_long']})  short $/tr {base[k]['short_pt']:+.2f} (n {base[k]['n_short']})")
# permutation of the pick's own directions within each period (keeps the long/short count): does the fade assignment matter?
rng = np.random.default_rng(11)
elig = np.where((s != 0) & S.entry_ok())[0]
ti = d.index[elig]
for k in ('TRAIN', 'TEST'):
    lo, hi = P[k]
    msk = (ti >= pd.Timestamp(lo)) & (ti < pd.Timestamp(hi))
    idx = elig[msk]; dirs = s[idx]
    vals = []
    for z in range(200):
        sp = np.zeros(len(s)); sp[idx] = rng.permutation(dirs)
        dz, Tz = S.run(sp); vals.append(pd_(dz, Tz, k))
    vals = np.array(vals)
    print(f"  permuted directions {k} (200 perms, same long count): mean {vals.mean():+.3f} sd {vals.std():.3f}; share >= pick {(vals >= base[k]['per_day']).mean():.3f}")
# random direction with P(long) equal to the pick's long share in that period
for k in ('TRAIN', 'TEST'):
    ls = base[k]['long_share']; vals = []
    for z in range(50):
        r = np.where(np.random.default_rng(1000 + z).random(len(s)) < ls, 1, -1)
        dz, Tz = S.run(np.where(s != 0, r, 0)); vals.append(pd_(dz, Tz, k))
    vals = np.array(vals)
    print(f"  random with long prob {ls:.2f} {k}: mean {vals.mean():+.3f}; share >= pick {(vals >= base[k]['per_day']).mean():.2f}")

# drift decomposition on the traded bars (gross move from entry bid to exit bid, ignoring the stop)
c = d.close.values; o = d.open.values
for k in ('TRAIN', 'TEST'):
    lo, hi = P[k]
    t = T[(T.entry >= pd.Timestamp(lo)) & (T.entry < pd.Timestamp(hi))]
    g = c[t.xi.values] - o[t.ei.values + 1]
    dr = t.dir.values
    mu = g.mean(); tot = (dr * g).sum()
    beta = mu * dr.sum(); alpha = (dr * (g - mu)).sum()
    se = np.std(dr * (g - mu), ddof=1) * np.sqrt(len(g))
    print(f"  {k}: gross dir*move total {tot:+.1f} = drift part (mean move {mu:+.2f} x net long {int(dr.sum())}) {beta:+.1f} "
          f"+ fade part {alpha:+.1f} (t {alpha / se:+.2f}); mean move after up-spikes {g[dr == -1].mean():+.2f}, after down-spikes {g[dr == 1].mean():+.2f}")

print('\n=== (3) costs / fills / latency, $/day TRAIN | TEST  ($/trade)')
V = {}
V['base FAIR'] = (days, T)
V['bar spread'] = S.run(s, spread='bar')
V['flat $0.30'] = S.run(s, spread=0.30)
V['flat $0.40'] = S.run(s, spread=0.40)
V['OHLC fill'] = S.run(s, fill='OHLC')
V['STOP fill'] = S.run(s, fill='STOP')
V['latency 1 bar'] = S.run(s, latency=1)
V['latency 2 bars'] = S.run(s, latency=2)
V['spread < $0.30 only'] = S.run(s, max_spread=0.30, strict_lt=True)
V['no spread filter'] = S.run(s, max_spread=99.0)
V['zero spreads filled by hour (alt loader)'] = None
for nm, v in V.items():
    if v is None: continue
    a = per(*v, *TRAIN); b = per(*v, *TEST)
    print(f"  {nm:28s} {a['per_day']:+.3f} | {b['per_day']:+.3f}   ({a['per_trade']:+.3f} | {b['per_trade']:+.3f}; trades {a['trades']} | {b['trades']})")
a = per(days, T, *TRAIN, extra=0.07); b = per(days, T, *TEST, extra=0.07)
print(f"  {'base + $0.07 commission':28s} {a['per_day']:+.3f} | {b['per_day']:+.3f}   ({a['per_trade']:+.3f} | {b['per_trade']:+.3f})")
d2 = load_m15(zero_fill='hour'); S2 = Sim(d2); s2, _ = sig_A(d2); v = S2.run(s2)
print(f"  {'zero spread -> hour median':28s} {per(*v, *TRAIN)['per_day']:+.3f} | {per(*v, *TEST)['per_day']:+.3f}")
# stop slippage
for k in ('TRAIN', 'TEST'):
    lo, hi = P[k]
    t = T[(T.entry >= pd.Timestamp(lo)) & (T.entry < pd.Timestamp(hi))]
    nst = int((t.pnl <= -24.99).sum()); nd = base[k]['days']
    print(f"  {k}: stops hit {nst} of {len(t)} trades; $/day with $1 / $3 stop slippage: {base[k]['per_day'] - nst / nd:+.3f} / {base[k]['per_day'] - 3 * nst / nd:+.3f}")
# 4-bar-old position at 23:00: how many trades were force-closed at session end vs timeout vs stop
for k in ('TRAIN', 'TEST'):
    lo, hi = P[k]
    t = T[(T.entry >= pd.Timestamp(lo)) & (T.entry < pd.Timestamp(hi))]
    print(f"  {k}: exits by bars held: " + str(t.bars.value_counts().sort_index().to_dict()))

print('\n=== (5) per-day report and concentration')
for k in P:
    r = base[k]
    print(f"  {k}: {r['per_day']:+.3f}/d, {r['trades_day']:.3f} tr/d, win {r['win']:.3f}, {r['per_trade']:+.3f}/tr (sd {r['sd_trade']:.2f}, t {r['tstat']:+.2f}), "
          f"days>=+5 {r['days_ge5']:.3f}, losing days {r['losing_days']:.3f}, active days {r['active_days']}/{r['days']}, worst day {r['worst_day']:+.2f}, "
          f"worst trade {r['worst_trade']:+.2f}, maxDD {r['max_dd']:+.2f}, total {r['total']:+.1f}; long total {r['long_total']:+.1f} short total {r['short_total']:+.1f}; "
          f"top-5 days {r['top5_sum']:+.1f} = {r['top5_share']:.2f} of total; breakeven extra cost/trade {r['per_trade']:+.3f}")
    lo, hi = P[k]
    p = days.pnl[(days.index >= pd.Timestamp(lo)) & (days.index < pd.Timestamp(hi))]
    srt = p.sort_values(ascending=False)
    for kk in (1, 3, 5, 10):
        print(f"     without best {kk:2d} days: {srt.iloc[kk:].sum() / len(p):+.3f}/d (total {srt.iloc[kk:].sum():+.1f})", end=';')
    print()
    # day bootstrap
    bs = np.array([np.random.default_rng(z).choice(p.values, len(p)).mean() for z in range(2000)])
    print(f"     day-bootstrap 90% CI of $/day [{np.quantile(bs, .05):+.3f}, {np.quantile(bs, .95):+.3f}], P($/day<=0) {(bs <= 0).mean():.3f}")
    act = p[p != 0]
    print(f"     best 5 days: " + ', '.join(f"{i.date()} {v:+.1f}" for i, v in srt.head(5).items()) +
          " | worst 5: " + ', '.join(f"{i.date()} {v:+.1f}" for i, v in srt.tail(5).items()))
q = days.pnl.groupby(days.index.to_period('Q')).agg(['mean', 'sum'])
qt = T.groupby(T.entry.dt.to_period('Q')).pnl.agg(['size', 'mean'])
print('  quarters $/day [trades]: ' + '; '.join(f"{i} {q.loc[i, 'mean']:+.2f} [{int(qt['size'].get(i, 0))}]" for i in q.index))
print(f"  positive quarters {(q['mean'] > 0).sum()}/{len(q)}")
y = days.pnl.groupby(days.index.year).mean(); yt = T.groupby(T.entry.dt.year).pnl.agg(['size', 'mean'])
yl = T[T.dir == 1].groupby(T[T.dir == 1].entry.dt.year).pnl.agg(['size', 'sum']); ys = T[T.dir == -1].groupby(T[T.dir == -1].entry.dt.year).pnl.agg(['size', 'sum'])
print('  years $/day [trades, $/tr] long total / short total: ' + '; '.join(
    f"{i} {y[i]:+.2f} [{int(yt.loc[i, 'size'])}, {yt.loc[i, 'mean']:+.2f}] L{yl['sum'].get(i, 0):+.0f}({int(yl['size'].get(i, 0))}) S{ys['sum'].get(i, 0):+.0f}({int(ys['size'].get(i, 0))})" for i in y.index))
# M1 era and pre-M1
for nm, lo, hi in (('pre-M1 2022-07..2026-06-25', '2022-07-01', '2026-06-26'), ('M1 era 2026-06-26..10-09', '2026-06-26', '2026-10-10'),
                   ('2025-01..2026-06-25', '2025-01-01', '2026-06-26')):
    r = per(days, T, lo, hi)
    print(f"  {nm}: {r['per_day']:+.3f}/d {r['per_trade']:+.2f}/tr trades {r['trades']} long share {r['long_share']:.2f}")
