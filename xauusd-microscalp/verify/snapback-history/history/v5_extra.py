"""Step 5: (a) pick C on M15 bars built from M1 at all 15 window offsets (M1 era, real M1 spreads);
(b) the user's TP range: same entries with TP $1 / $0.50; (c) stop stress: slipped stops and a failed stop;
(d) per-year $/trade in units of the average range."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history')
from vlib import *
m1 = load('M1')
print('(a) M15-from-M1 at each window offset, M1 era (2026-06-26..10-09), base cost = min M1 spread in the bar + $0.05')
res = []
for off in range(15):
    g = m1.resample('15min', offset=f'{off}min', label='left', closed='left')
    q = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(), 'close': g.close.last(),
                      'tick_volume': g.tick_volume.sum(), 'spread': g.spread.min(), 'cnt': g.open.count()})
    q = finish(q[q.cnt >= 12].drop(columns='cnt'))
    fq, _ = features(q, 15); sq = signal(q, fq, 2, 4.0, 1); E = Eng(q, 15)
    days, T = E.run(sq, 2, 25, 3)
    days = days[days.index >= '2026-06-29']; T = T[T.entry >= '2026-06-29']     # AR needs 32 bars of history
    st = stats(days, T); res.append(st['per_day'])
    print(f"  offset {off:2d}: {fmt(st)}")
res = np.array(res)
print(f"  15 offsets: mean {res.mean():+.3f}/day, median {np.median(res):+.3f}, positive {int((res > 0).sum())}/15, min {res.min():+.2f}, max {res.max():+.2f}")

d = load('M15'); f, _ = features(d, 15); s = signal(d, f, 2, 4.0, 1); E = Eng(d, 15)
P = {'TRAIN': ('2022-07-01', '2025-01-01'), 'TEST': ('2025-01-01', None), 'M1ERA': ('2026-06-26', None)}
print('\n(b) user TP range: pick C entries with a take-profit (same 30-min time exit, $25 stop)')
for tp in (1.0, 0.5, 0.3):
    for fill in ('FAIR', 'OHLC', 'STOP'):
        days, T = E.run(s, 2, 25, 3, tp=tp, fill=fill)
        print(f"  TP {tp} {fill}: " + ' | '.join(f"{p} {stats(days, T, lo, hi)['per_day']:+.3f}/d {stats(days, T, lo, hi)['per_trade']:+.3f}/tr win {stats(days, T, lo, hi)['win']:.2f}" for p, (lo, hi) in P.items()))
print('\n(c) stop stress')
days, T = E.run(s, 2, 25, 3)
stop = T.pnl <= -24.5
for slip in (0, 5, 10, 20):
    adj = T.pnl - slip * stop
    dd = days.copy(); dd['pnl'] = adj.groupby(T.entry.dt.normalize()).sum().reindex(days.index, fill_value=0.0)
    print(f"  stop slips ${slip:2d}: " + ' | '.join(f"{p} {stats(dd, T.assign(pnl=adj), lo, hi)['per_day']:+.3f}/d" for p, (lo, hi) in P.items()))
d0, T0 = E.run(s, 2, 1000, 3)
print(f"  no stop at all (failed stop): worst trade {T0.pnl.min():+.1f} ({T0.entry[T0.pnl.idxmin()]}), worst day {d0.pnl.min():+.1f}, "
      + ' | '.join(f"{p} {stats(d0, T0, lo, hi)['per_day']:+.3f}/d" for p, (lo, hi) in P.items()))
# synthetic news spike: every pick-C trade suffers an extra adverse jump of $X during the hold that the stop fills at the
# jump's far end (gap through the stop), i.e. loss = max(stop, X) on the share of trades hit by such a spike
print('  what one $20-40 adverse jump costs: with the stop at $25 a $20 jump does not stop out (closing P&L depends on retrace);'
      ' a $40 gap through the stop costs $40 per open position, up to 2 positions open at once in this rule -> $80')
print('\n(d) $/trade over AR by year:', ' '.join(f"{y}: {g.pnl.mean():+.2f}$ {(g.pnl / f.ar.values[g.ei.values]).mean():+.3f}AR n{len(g)}"
                                           for y, g in T.groupby(T.entry.dt.year)))
print('configurations scored in this step: 15 offsets + 9 TP variants + stress variants on the pick (not selections)')
