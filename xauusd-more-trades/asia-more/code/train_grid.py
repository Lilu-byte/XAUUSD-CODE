"""Score every version on m15_train ONLY (M15, 11 Jul 2022 - 28 Jun 2024, $ scaled to price/4000)
and pick at most 3 candidates by a rule fixed before running it.

Families (all one 0.01 lot, costs as the EA copy):
  A  re-arm: after the day's trade closes (TP only / TP or SL), take the next fresh break
     (back inside the range then out again / close beyond the day's high-low so far), up to
     2 or 3 trades a day; re-armed trades at TP 3/5/8, SL 30/50 (first trade unchanged).
  A2 re-arm with the TP/SL changed for ALL trades (first trade too), 3 trades a day, after TP.
  B  stop and reverse: after a same-day stop-out, trade once the other way (next break of the
     other side of the range / straight away), TP 5/8 SL 30/50; and SAR on top of re-arm.
  C  a second range as its own one-trade-a-day stream (range start-end, broken after the end),
     TP 3/5/8, SL 30/50.
  D  a second position on the same first break with a bigger target (TP 8 or 12).

Selection rule (fixed before the run):
  eligible  = adds >= 0.30 trades/day to the pair on m15_train AND the candidate alone (extra
              trades, added stream, or changed-EA minus base EA) makes > $0/day on m15_train.
  holds     = combined per_day >= 1.93 AND combined max_dd >= -323 AND max_dd_mtm >= -344
              (baseline -313 / -334 plus $10 of slack, as the pass rule allows on the other windows).
  Pick the best version (by combined per_day) of each family group {A/A2/B-with-rearm},
  {C}, {D/B}, choosing among 'holds' versions first, else among 'eligible' ones. If a group
  has no eligible version its slot goes unused (fewer than 3 candidates).
Usage: python3 -I train_grid.py   -> writes ../train_grid.csv, prints the summary.
"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/asia-more/code')
import json
import numpy as np, pandas as pd
import asia_more as A
H = A.H
W = 'm15_train'
OUT = '/mnt/project-files/xauusd-more-trades/asia-more/train_grid.csv'


def versions():
    V = []
    for rearm in ('tp', 'any'):
        for fresh in ('reinside', 'newext'):
            for mx in (2, 3):
                for rtp in (3, 5, 8):
                    for rsl in (30, 50):
                        V.append(('A', dict(kind='change', rearm=rearm, fresh=fresh, max_trades=mx, rearm_tp=rtp, rearm_sl=rsl)))
    for fresh in ('reinside', 'newext'):
        for tp, sl in ((3, 30), (3, 50), (5, 30), (8, 30), (8, 50)):
            V.append(('A2', dict(kind='change', rearm='tp', fresh=fresh, max_trades=3, tp=tp, sl=sl)))
    for sar in ('break', 'now'):
        for stp, ssl in ((5, 50), (5, 30), (8, 50), (8, 30)):
            V.append(('B', dict(kind='change', sar=sar, sar_tp=stp, sar_sl=ssl)))
    for rearm in ('tp', 'any'):
        for fresh in ('reinside', 'newext'):
            V.append(('B+A', dict(kind='change', sar='break', rearm=rearm, fresh=fresh, max_trades=3)))
    for rs, re_ in ((0, 360), (0, 420), (180, 540), (360, 540), (540, 720), (540, 780), (720, 900), (780, 960), (0, 720)):
        for tp in (3, 5, 8):
            for sl in (30, 50):
                V.append(('C', dict(kind='stream', range_start=rs, range_end=re_, tp=tp, sl=sl)))
    for tp, sl in ((8, 50), (8, 30), (12, 50)):
        V.append(('D', dict(kind='stream', tp=tp, sl=sl)))
    return V


def build(spec, window, base):
    """-> (combined parts dict, candidate-alone trades or daily series, changed EA or None)."""
    tf, scale = A.window_tf_scale(window)
    p = {k: v for k, v in spec.items() if k != 'kind'}
    t = A.asia_x(tf, scale=scale, **p)
    if spec['kind'] == 'stream':
        return {**base, 'Extra': t}, t, None
    comb = {'AllAgree': base['AllAgree'], 'AsiaBreak': t}
    if 'tp' in p or 'sl' in p:          # first trade changed too: alone = changed EA minus base EA, by day
        alone = H.per_day(t, window) - H.per_day(base['AsiaBreak'], window)
    else:
        alone = t[t.kind != 'first']
    return comb, alone, t


def alone_stats(alone, window):
    if isinstance(alone, pd.Series):
        return dict(per_day=round(alone.mean(), 2), extra_trades_day=None)
    s = H.per_day(alone, window)
    eq = s.cumsum()
    return dict(per_day=round(s.mean(), 2), extra_trades_day=round(len(H.in_window(alone, window)) / len(H.days(window)), 2),
                max_dd=round((eq - eq.cummax()).min(), 0))


if __name__ == '__main__':
    base = H.pair_parts(W)
    b = H.score(base, W)
    print('baseline pair m15_train', {k: b[k] for k in ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm')})
    rows = []
    V = versions()
    for fam, spec in V:
        comb, alone, t = build(spec, W, base)
        s = H.score(comb, W)
        a = alone_stats(alone, W)
        rows.append(dict(family=fam, spec=json.dumps(spec), per_day=s['per_day'], trades_day=s['trades_day'],
                         add_trades=round(s['trades_day'] - b['trades_day'], 2), max_dd=s['max_dd'],
                         max_dd_mtm=s['max_dd_mtm'], worst_month=s['worst_month'],
                         alone_per_day=a['per_day'], alone_max_dd=a.get('max_dd')))
    R = pd.DataFrame(rows)
    R['eligible'] = (R.add_trades >= 0.30) & (R.alone_per_day > 0)
    R['holds'] = R.eligible & (R.per_day >= 1.93) & (R.max_dd >= -323) & (R.max_dd_mtm >= -344)
    R.to_csv(OUT, index=False)
    print(f'versions scored on {W}: {len(R)}  (eligible {R.eligible.sum()}, holds the line {R.holds.sum()})')
    pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 120)
    cols = ['spec', 'per_day', 'add_trades', 'max_dd', 'max_dd_mtm', 'alone_per_day']
    for fam in R.family.unique():
        g = R[R.family == fam]
        print(f'\n--- family {fam}: {len(g)} versions, alone>0 in {(g.alone_per_day > 0).sum()}, eligible {g.eligible.sum()}, holds {g.holds.sum()}; '
              f'combined per_day range {g.per_day.min()} .. {g.per_day.max()}')
        print(g.sort_values('per_day', ascending=False)[cols].head(5).to_string(index=False))
    picks = []
    for grp in (('A', 'A2', 'B+A'), ('C',), ('D', 'B')):
        g = R[R.family.isin(grp)]
        pool = g[g.holds] if g.holds.any() else g[g.eligible]
        if len(pool):
            picks.append(pool.sort_values('per_day', ascending=False).iloc[0])
    print('\nPICKED (by the fixed rule):')
    for p in picks:
        print(' ', p.family, p.spec, {k: p[k] for k in ('per_day', 'add_trades', 'max_dd', 'max_dd_mtm', 'alone_per_day', 'holds')})
    with open('/mnt/project-files/xauusd-more-trades/asia-more/picks.json', 'w') as f:
        json.dump([dict(family=p.family, spec=json.loads(p.spec)) for p in picks], f, indent=1)
