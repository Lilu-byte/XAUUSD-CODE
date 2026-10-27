"""(3) Tail risk of P2 on a $3,000 account (0.01 lot, $1 per $1).
  a) M1 (TRAIN+TEST, base spread, FAIR, next-bar open): worst day/trade/week, losing streaks, drawdown, $25-stop hits
  b) exposure clustering: how often 3 positions are open on the same side
  c) news-size bars in the data: what P2 did when an M1 bar had a range >= $10 / $15 / $20
  d) synthetic spike: at moments when P2 holds 3 positions, the next bar is replaced by an adverse $20/$30/$40 move
     (price level shifted for the rest of the day); re-simulated with the same simulator; plus a slippage overlay
  e) history ports (M5 2025-05..2026-10, M15 2022-07..2026-10): worst day / week / month and stop hits
  f) day-bootstrap of one trading year (250 days) from TEST days and from the M5-port pre-2026 days"""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *
import warnings; warnings.filterwarnings('ignore')


def streaks(x):
    best = cur = 0
    for v in x:
        cur = cur + 1 if v else 0; best = max(best, cur)
    return best


def tails(name, d, t, a=None, b=None):
    sel = np.ones(len(d), bool)
    if a is not None: sel &= d.index >= a
    if b is not None: sel &= d.index < b
    dd = d[sel]
    tt = t[t.entry.dt.normalize().isin(dd.index)].sort_values('entry')
    p = dd.pnl; eq = p.cumsum(); dd_ = (eq - eq.cummax())
    wk = p.groupby(p.index.to_period('W')).sum(); mo = p.groupby(p.index.to_period('M')).sum()
    stop = tt.pnl <= -24.99
    print(f'{name}: days {len(p)}, trades {len(tt)}; worst day {p.min():+.1f} ({p.idxmin().date()}), worst trade {tt.pnl.min():+.2f}, '
          f'worst week {wk.min():+.1f} ({wk.idxmin()}), worst month {mo.min():+.1f}, max DD {dd_.min():+.1f} (= {dd_.min() / 30:+.1f}% of $3,000); '
          f'longest losing streak {streaks(tt.pnl.values <= 0)} trades / {streaks(p.values < 0)} days; '
          f'$25-stop hits {int(stop.sum())} ({stop.mean() * 100:.1f}% of trades, total {tt.pnl[stop].sum():+.0f}); '
          f'trades <= -$10: {(tt.pnl <= -10).mean() * 100:.1f}%; P&L p1/p5/p50/p95/p99 ' +
          '/'.join(f'{v:+.1f}' for v in np.percentile(tt.pnl, [1, 5, 50, 95, 99])))
    return p


m = load_tf('M1'); A = Arr(m); s = A.signal()
d, t = A.run(s)
print('=== a) M1, base spread')
for nm, a, b in (('TRAIN', None, SPLIT), ('TEST', SPLIT, None), ('ALL', None, None)):
    tails(f'  P2 {nm}', d, t, a, b)
pt = d[d.index >= SPLIT].pnl
print('  TEST weekly $: ' + ' '.join(f'{v:+.0f}' for v in pt.groupby(pt.index.to_period('W')).sum().values))
print('  TEST best 3 days ' + ', '.join(f'{v:+.0f}' for v in pt.nlargest(3).values) + f'; TEST $/day without them {pt.drop(pt.nlargest(3).index).mean():+.2f}; '
      f'worst 3 days ' + ', '.join(f'{v:+.0f} ({i.date()})' for i, v in pt.nsmallest(3).items()))

print('\n=== b) exposure clustering (ALL)')
ei, xi, dr = t.ei.values, t.xi.values, t.dir.values
openn = np.zeros(len(m), int); side = np.zeros(len(m), int)
for a_, b_, s_ in zip(ei, xi, dr):
    openn[a_ + 1:b_ + 1] += 1; side[a_ + 1:b_ + 1] += s_
inmkt = openn > 0
print(f'  minutes in the market {inmkt.mean() * 100:.1f}% of session minutes; with 3 positions open {(openn == 3).mean() * 100:.1f}% '
      f'(all same side {((openn == 3) & (np.abs(side) == 3)).mean() * 100:.1f}%); share of trades opened while 2 others are open on the same side: '
      f'{np.mean([abs(side[i + 1]) == 3 for i in ei]) * 100:.1f}%')
# clusters: trades whose holding windows overlap
order = np.argsort(ei); cl = np.zeros(len(t), int); c_id = 0; end = -1
for j in order:
    if ei[j] > end: c_id += 1
    cl[j] = c_id; end = max(end, xi[j])
cs = pd.Series(t.pnl.values).groupby(cl).sum()
print(f'  overlapping-trade clusters {len(cs)}: worst cluster {cs.min():+.1f}, clusters <= -$50: {(cs <= -50).sum()}, <= -$75: {(cs <= -75).sum()}')

print('\n=== c) news-size M1 bars in the M1 file and P2 around them')
rng_ = m.high - m.low
for th in (10, 15, 20, 30):
    big = np.flatnonzero(rng_.values >= th)
    hit = [j for j in range(len(t)) if np.any((big > ei[j]) & (big <= xi[j]))]
    after = [j for j in range(len(t)) if np.any((big <= ei[j]) & (big >= ei[j] - 2))]
    print(f'  bars with range >= ${th}: {len(big)} ({len(big) / len(A.dates):.2f}/day); P2 trades open through one: {len(hit)} '
          f'(sum {t.pnl.values[hit].sum():+.0f}, mean {t.pnl.values[hit].mean() if hit else np.nan:+.2f}); trades entered within 2 bars after one: '
          f'{len(after)} (mean {t.pnl.values[after].mean() if after else np.nan:+.2f}, worst {t.pnl.values[after].min() if after else np.nan:+.1f})')
top = rng_.nlargest(5)
print('  5 largest M1 bars: ' + '; '.join(f'{i} range ${v:.1f}' for i, v in top.items()))

print('\n=== d) synthetic adverse spike at moments P2 holds 3 same-side positions')
cand = np.flatnonzero((openn == 3) & (np.abs(side) == 3))
cand = cand[(A.tod[cand] < 1300)]
rs = np.random.default_rng(3).choice(cand, 60, replace=False)
base_day = d.pnl.values
for X in (20.0, 30.0, 40.0):
    extra = []; worst_day = []
    for j in rs:
        sd_ = int(np.sign(side[j])); dd_ = A.day[j]
        o, h, l, c = A.o.copy(), A.h.copy(), A.l.copy(), A.c.copy()
        same = np.flatnonzero((A.day == dd_) & (np.arange(len(m)) >= j))
        shift = -sd_ * X                         # adverse to the open positions
        o[same[1:]] += shift; h[same[1:]] += shift; l[same[1:]] += shift; c[same] += shift
        # bar j: opens at the previous close level, runs X against the positions, closes there
        o[j] = A.c[j - 1]
        if sd_ > 0: h[j] = max(A.c[j - 1], A.h[j]); l[j] = min(A.l[j] + shift, c[j])
        else: l[j] = min(A.c[j - 1], A.l[j]); h[j] = max(A.h[j] + shift, c[j])
        from ea_sim import _sim_next
        sig = A.ea_filter(s)
        dp, *_ = _sim_next(o, h, l, c, A.spread('base'), A.tod, A.day, A.last, sig, 1000.0, 25.0, 15, 3, FILL['FAIR'], 0.0, 0.0, 0)
        extra.append(dp[dd_] - base_day[dd_]); worst_day.append(dp[dd_])
    extra = np.array(extra); worst_day = np.array(worst_day)
    print(f'  adverse ${X:.0f} one-minute spike (60 random 3-position moments): day P&L change mean {extra.mean():+.1f}, worst {extra.min():+.1f}; '
          f'resulting day P&L worst {worst_day.min():+.1f}; with the $25 stops filled at the spike bar close instead (fast-market slippage) '
          f'the 3 positions lose about {-3 * (X + 0.2):+.0f} instead of {-3 * (min(X, 25.0) + 0.2):+.0f}')

print('\n=== e) history ports (flat $0.20), worst periods')
for tf, natr, hold, k in (('M5', 48, 3, 1.05), ('M5', 48, 3, 1.35), ('M15', 16, 1, 1.30), ('M15', 16, 1, 0.59)):
    mm = load_tf(tf); B = Arr(mm, tf); sg = B.signal(k=k, L=1, atr_n=natr)
    dB, tB = B.run(sg, sl=25.0, hold=hold, mo=3, spr=0.20)
    pB = tails(f'  {tf} k {k:.2f} hold {hold}', dB, tB)
    if tf == 'M5' and k == 1.05:
        pre26 = pB[pB.index < pd.Timestamp('2026-01-01')]

print('\n=== f) one trading year (250 days) by day-bootstrap, 5,000 paths')
rng = np.random.default_rng(42)
for nm, pool in (('TEST days (M1, 29 days)', pt.values), ('TRAIN days (M1, 47 days)', d[d.index < SPLIT].pnl.values),
                 ('M5 port k1.05, 2025-05..2025-12 days (no-edge regime)', pre26.values)):
    P = rng.choice(pool, (5000, 250)); eq = P.cumsum(1); ddm = (eq - np.maximum.accumulate(eq, 1)).min(1)
    print(f'  {nm}: year total median {np.median(eq[:, -1]):+.0f} (5%: {np.percentile(eq[:, -1], 5):+.0f}); P(year < 0) {np.mean(eq[:, -1] < 0):.2f}; '
          f'max DD median {np.median(ddm):+.0f}, 5% worst {np.percentile(ddm, 5):+.0f}; P(DD worse than -$300 / -$600) '
          f'{np.mean(ddm < -300):.2f} / {np.mean(ddm < -600):.2f}')
