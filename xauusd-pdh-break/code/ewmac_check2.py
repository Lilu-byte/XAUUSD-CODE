"""EWMAC: when the worst drop happened, a 1-unit cap (max 0.01 lot), and next to the pair (18 Oct 2026)."""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
import pdh as P, others as O
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/code'); import harness as H
for cap, name in ((2.0, 'default 0-4 units'), (0.5, 'Cap=0.5 -> 0-1 unit')):
    e = O.ewmac(cap=cap)
    dd = e.groupby(e.index.normalize()).sum(); eq = dd.cumsum(); dr = eq - eq.cummax()
    lo = dr.idxmin(); pk = eq[:lo].idxmax()
    print(f'{name}: worst drop ${dr.min():.0f} from {pk.date()} to {lo.date()}')
    for a, b in (('2016-08-01', '2021-06-30'), ('2021-07-01', '2026-10-09'), ('2025-05-06', '2026-10-09')):
        s = dd[a:b]; q = s.cumsum(); m = s.groupby(s.index.to_period('M')).sum()
        print(f'   {a}..{b}: $/day {s.sum()/len(pd.bdate_range(a,b)):.2f}, dd ${(q-q.cummax()).min():.0f}, worst month ${m.min():.0f}, '
              f'losing months {(m<0).mean():.0%}, by year', s.groupby(s.index.year).sum().round(0).astype(int).to_dict())
    for w in ('pair', 'm15_test'):
        D = H.days(w); pair = sum(H.per_day(t, w) for t in H.pair_parts(w).values())
        ew = dd.reindex(D, fill_value=0.0)   # weekend bars folded into nothing; tiny
        tot = pair + ew; q = tot.cumsum(); qe = ew.cumsum()
        print(f'   {w}: pair $/day {pair.mean():.2f}, EWMAC {ew.mean():.2f}, together {tot.mean():.2f}, '
              f'dd together ${(q-q.cummax()).min():.0f} (pair alone {(pair.cumsum()-pair.cumsum().cummax()).min():.0f}), corr {pair.corr(ew):.2f}')
