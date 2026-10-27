"""Score every version of the family on m15_train ONLY and pick at most 3 candidates.

Pre-registered (written before the grid was run):
- Baseline on m15_train = harness.pair_parts('m15_train'): $1.93/day, 1.24 trades/day,
  max_dd -$313, max_dd_mtm -$334.
- Costs: a CHANGE to GoldAllAgree is priced like the EA replay the baseline uses (bar's recorded
  spread). Because that spread is the lowest in each bar and faster rules trade more, a change must
  also beat the baseline when BOTH are priced at the task's flat $0.30 spread + $0.10 slippage a
  fill. An ADDED stream is priced at the flat $0.30 + $0.10 a fill.
- A version is ELIGIBLE when on m15_train:
    E1 combined trades/day >= 1.24 + 0.12 (= +0.3 on the pair window, scaled by GoldAllAgree's
       M15/M5 trade ratio 0.28/0.71 ~ 0.4);
    E2 combined $/day >= 1.93 (for a change also: fixed-cost changed pair >= fixed-cost baseline);
    E3 combined max_dd >= -323 and max_dd_mtm >= -344 (the pass rule's $10 slack);
    E4 the candidate's own P&L > 0 (added stream alone; for a change, changed EA minus the EA).
- Families: (1) change to GoldAllAgree (EMA, timeframes, k-of-n, re-entry, cool-down);
  (2) short mirror stream; (3) sibling stream. Pick the eligible version with the best combined
  $/day in each family. If a family has none eligible: among versions meeting E1, E2 and E4, the
  one with the smallest drawdown excess (worse of the two dd misses); if none, the E1 version with
  the best combined $/day.
- h1_old is not used to choose anything (hindsight.py looks at it afterwards, incl. the short side).
Usage: python3 -I train_grid.py  -> ../train_grid.csv, ../picks.json and a printed summary."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/allagree-more/code')
import json
import numpy as np, pandas as pd
import aa_more as A, specs as SP
H = A.H
D = '/mnt/project-files/xauusd-more-trades/allagree-more/'
W = 'm15_train'
FAM = {'change/agree': 'change', 'change/armed': 'change', 'change/cool': 'change', 'short': 'short', 'sibling': 'sibling'}


def evaluate(spec, w, base_parts, base_fix_parts):
    kind, t = SP.build(spec, w)
    asia = base_parts['AsiaBreak']
    if kind == 'change':
        comb = {'AllAgree': t, 'AsiaBreak': asia}
        _, tf = SP.build(spec, w, cost='fixed')
        comb_fix = {'AllAgree': tf, 'AsiaBreak': asia}
        own = H.per_day(t, w) - H.per_day(base_parts['AllAgree'], w)
    else:
        comb = {**base_parts, 'cand': t}
        comb_fix = None
        own = H.per_day(t, w)
    s = H.score(comb, w, by_period=False)
    r = dict(name=SP.name(spec), family=FAM[spec['kind']], kind=kind,
             per_day=s['per_day'], trades_day=s['trades_day'], max_dd=s['max_dd'], max_dd_mtm=s['max_dd_mtm'],
             worst_month=s['worst_month'], own_per_day=round(own.mean(), 2),
             alone_per_day=round(H.per_day(t, w).mean(), 2), alone_trades_day=round(len(H.in_window(t, w)) / len(H.days(w)), 2))
    if comb_fix is not None:
        r['per_day_fixed'] = round(sum(H.per_day(x, w) for x in comb_fix.values()).mean(), 2)
    return r


if __name__ == '__main__':
    base = H.pair_parts(W)
    bfix = {'AllAgree': A.baseline_aa(W, 'fixed'), 'AsiaBreak': base['AsiaBreak']}
    b = H.score(base, W, by_period=False)
    b_fix = round(sum(H.per_day(x, W) for x in bfix.values()).mean(), 2)
    print('baseline', {k: b[k] for k in ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm')}, 'fixed-cost $/day', b_fix)
    G = SP.grid(); rows = []
    for i, spec in enumerate(G):
        r = evaluate(spec, W, base, bfix); r['spec'] = json.dumps(spec); rows.append(r)
        if i % 25 == 0: print(i, r['name'], r['per_day'], r['trades_day'], r['max_dd'], r['max_dd_mtm'], flush=True)
    T = pd.DataFrame(rows)
    T['E1'] = T.trades_day >= b['trades_day'] + 0.12
    T['E2'] = (T.per_day >= b['per_day']) & ((T.kind != 'change') | (T.per_day_fixed >= b_fix))
    T['E3'] = (T.max_dd >= b['max_dd'] - 10) & (T.max_dd_mtm >= b['max_dd_mtm'] - 10)
    T['E4'] = T.own_per_day > 0
    T['eligible'] = T.E1 & T.E2 & T.E3 & T.E4
    T['dd_excess'] = np.maximum(0, np.maximum((b['max_dd'] - 10) - T.max_dd, (b['max_dd_mtm'] - 10) - T.max_dd_mtm))
    T.to_csv(D + 'train_grid.csv', index=False)
    picks = []
    for fam in ('change', 'short', 'sibling'):
        F = T[T.family == fam]
        print(f'\n{fam}: {len(F)} versions, E1 {F.E1.sum()}, E2 {F.E2.sum()}, E3 {F.E3.sum()}, E4 {F.E4.sum()}, eligible {F.eligible.sum()}')
        if F.eligible.any():
            p = F[F.eligible].sort_values('per_day', ascending=False).iloc[0]; how = 'eligible, best $/day'
        elif (F.E1 & F.E2 & F.E4).any():
            p = F[F.E1 & F.E2 & F.E4].sort_values(['dd_excess', 'per_day'], ascending=[True, False]).iloc[0]; how = 'none eligible: smallest dd excess among E1+E2+E4'
        elif F.E1.any():
            p = F[F.E1].sort_values('per_day', ascending=False).iloc[0]; how = 'none eligible: best $/day among E1'
        else:
            print('  nothing meets E1'); continue
        print('  pick:', p['name'], '|', how)
        print('  ', {k: p[k] for k in ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm', 'own_per_day', 'alone_per_day')})
        cols = ['name', 'per_day', 'trades_day', 'max_dd', 'max_dd_mtm', 'own_per_day', 'E1', 'E2', 'E3', 'E4']
        print(F.sort_values('per_day', ascending=False)[cols].head(8).to_string(index=False))
        picks.append(dict(family=fam, how=how, spec=json.loads(p['spec']), name=p['name']))
    json.dump(picks, open(D + 'picks.json', 'w'), indent=1)
    print('\nversions scored on m15_train:', len(T))
