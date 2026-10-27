"""Training grid on m15_train ONLY, and the pre-registered pick of at most 3 candidates.

Versions: 15 signals x TP {5, 8} x SL {30, 50} x gate {none, entry, strict} = 180, all on m15_train.
  NY first half hour / first hour: move(16:30, 17:00) and move(16:30, 17:30), with (+1) or against (-1)   -> 4
  London session move at 15:30: move(10:00, 15:30), with or against, min move $0 or $10          -> 4
  H1 EMA20/80 direction at 11:00, 13:00, 15:00, 17:00, 19:00                                       -> 5
  Pullback to the H1 EMA20 in the H4 direction (10:00-20:00), H4 only or H4 + H1 agreeing         -> 2

Pick rule (written before the grid was run):
  1. Candidates must be gated (gate 'entry' or 'strict'); ungated versions are scored for reference.
  2. Eligible: stream alone > $0/day and >= 0.30 trades/day on m15_train, and pair + stream on
     m15_train has max_dd no deeper than -$323 and max_dd_mtm no deeper than -$344 (baseline
     -$313 / -$334 plus the same $10 slack the pass test allows).
  3. Best eligible version of each family (NY, London, H1EMA, Pullback) by the stream's own $/day;
     the 3 best families go forward.
  4. If fewer than 3 families have an eligible version, fill the gap with each remaining family's
     best gated version that is > $0/day and >= 0.30 trades/day (drawdown ignored), by $/day.
Writes ../grid_m15_train.csv and ../candidates.json. Run: python3 -I grid.py
"""
import sys; sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/idle-time/code')
import json, itertools, numpy as np, pandas as pd
import idle as I, harness as H

OUT = '/mnt/project-files/xauusd-more-trades/idle-time/'

SIGNALS = []
for end in (17 * 60, 17 * 60 + 30):
    for mode in (1, -1):
        SIGNALS.append(('NY', dict(kind='move', start=16 * 60 + 30, end=end, mode=mode)))
for mode in (1, -1):
    for thr in (0.0, 10.0):
        SIGNALS.append(('London', dict(kind='move', start=10 * 60, end=15 * 60 + 30, mode=mode, thr=thr)))
for T in (11, 13, 15, 17, 19):
    SIGNALS.append(('H1EMA', dict(kind='h1ema', T=T * 60)))
for need in (False, True):
    SIGNALS.append(('Pullback', dict(kind='pullback', need_h1=need)))
TPS, SLS, GATES = (5.0, 8.0), (30.0, 50.0), ('none', 'entry', 'strict')


def label(spec):
    k = spec['kind']
    if k == 'move':
        f = lambda m: f'{m // 60:02d}:{m % 60:02d}'
        s = f"move {f(spec['start'])}-{f(spec['end'])} {'with' if spec['mode'] == 1 else 'against'}"
        return s + (f" min${spec['thr']:.0f}" if spec.get('thr') else '')
    if k == 'h1ema': return f"H1 EMA20/80 at {spec['T'] // 60:02d}:00"
    return 'pullback H1EMA20, H4' + (' + H1' if spec['need_h1'] else '')


class Base:
    """The pair's daily P&L and mark-to-market equity on a window, so pair + stream can be scored
    quickly (H.score is additive over parts; evaluate.py re-checks every number with H.score)."""
    def __init__(self, window):
        self.w = window; P = I.pair(window)
        self.daily = sum(H.per_day(t, window) for t in P.values())
        self.mtm = sum(H.mtm_daily(t, window) for t in P.values())
        self.ntr = sum(len(H.in_window(t, window)) for t in P.values())
        self.nd = len(H.days(window))

    def score(self, t):
        d = self.daily + H.per_day(t, self.w); q = self.mtm + H.mtm_daily(t, self.w)
        eq = d.cumsum(); m = d.groupby(d.index.to_period('M')).sum()
        return dict(per_day=round(d.mean(), 2), trades_day=round((self.ntr + len(H.in_window(t, self.w))) / self.nd, 2),
                    max_dd=round((eq - eq.cummax()).min(), 0), max_dd_mtm=round((q - q.cummax()).min(), 0),
                    worst_month=round(m.min(), 0))


def alone(t, w):
    d = H.per_day(t, w); eq = d.cumsum()
    return dict(per_day=round(d.mean(), 2), trades_day=round(len(H.in_window(t, w)) / len(H.days(w)), 2),
                max_dd=round((eq - eq.cummax()).min(), 0))


if __name__ == '__main__':
    W = 'm15_train'; base = Base(W)
    # spot-check the fast scorer against H.score once
    t = I.stream(W, SIGNALS[0][1], 5.0, 50.0, 'entry'); P = I.pair(W)
    ref = H.score({**P, 'x': t}, W); mine = base.score(t)
    assert all(abs(ref[k] - mine[k]) < 0.011 for k in mine), (ref, mine)
    rows = []
    for (fam, spec), tp, sl, gate in itertools.product(SIGNALS, TPS, SLS, GATES):
        t = I.stream(W, spec, tp, sl, gate)
        a = alone(t, W); c = base.score(t)
        rows.append(dict(family=fam, signal=label(spec), spec=json.dumps(spec), tp=tp, sl=sl, gate=gate,
                         alone_per_day=a['per_day'], alone_trades_day=a['trades_day'], alone_max_dd=a['max_dd'],
                         win_rate=round((t.pnl > 0).mean(), 3) if len(t) else np.nan,
                         comb_per_day=c['per_day'], comb_max_dd=c['max_dd'], comb_max_dd_mtm=c['max_dd_mtm'],
                         comb_worst_month=c['worst_month']))
    G = pd.DataFrame(rows)
    G.to_csv(OUT + 'grid_m15_train.csv', index=False)
    print(f'{len(G)} versions scored on m15_train (baseline pair $1.93/day, dd -313, mtm -334)')
    print('  stream > $0/day:', int((G.alone_per_day > 0).sum()), 'of', len(G))
    for g in GATES:
        s = G[G.gate == g]
        print(f'  gate {g:6s}: mean stream $/day {s.alone_per_day.mean():+.2f}, positive {int((s.alone_per_day > 0).sum())}/{len(s)}, '
              f'mean trades/day {s.alone_trades_day.mean():.2f}, mean combined mtm dd {s.comb_max_dd_mtm.mean():.0f}')
    for f in G.family.unique():
        s = G[G.family == f]
        print(f'  {f:8s}: mean stream $/day {s.alone_per_day.mean():+.2f}, positive {int((s.alone_per_day > 0).sum())}/{len(s)}')

    gated = G[G.gate != 'none']
    elig = gated[(gated.alone_per_day > 0) & (gated.alone_trades_day >= 0.30) &
                 (gated.comb_max_dd >= -323) & (gated.comb_max_dd_mtm >= -344)]
    print('eligible (gated, >0, >=0.30 trades/day, dd within slack):', len(elig))
    best = elig.sort_values(['alone_per_day', 'comb_max_dd_mtm'], ascending=False).drop_duplicates('family')
    picks = list(best.head(3).index)
    if len(picks) < 3:
        rest = gated[(gated.alone_per_day > 0) & (gated.alone_trades_day >= 0.30) &
                     ~gated.family.isin(G.loc[picks, 'family'])]
        fill = rest.sort_values('alone_per_day', ascending=False).drop_duplicates('family')
        picks += list(fill.head(3 - len(picks)).index)
        print('filled by rule 4:', len(picks) - len(best.head(3)))
    C = G.loc[picks]
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
    print(C.drop(columns='spec').to_string())
    # the ungated twin of each pick, for reference
    for i in picks:
        r = G.loc[i]
        u = G[(G.spec == r.spec) & (G.tp == r.tp) & (G.sl == r.sl) & (G.gate == 'none')].iloc[0]
        print(f'  ungated twin of [{r.signal} TP{r.tp:.0f} SL{r.sl:.0f}]: stream {u.alone_per_day:+.2f}/day '
              f'{u.alone_trades_day:.2f} tr/day, combined dd {u.comb_max_dd:.0f} mtm {u.comb_max_dd_mtm:.0f}')
    json.dump([dict(family=r.family, signal=r.signal, spec=json.loads(r.spec), tp=r.tp, sl=r.sl, gate=r.gate)
               for r in C.itertuples()], open(OUT + 'candidates.json', 'w'), indent=1)
