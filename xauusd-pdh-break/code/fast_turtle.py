"""Fast Turtle 20/10 (same EA, 20-day entry / 10-day exit) next to 55/20 and holding gold, 0.01 lot after costs (21 Oct 2026)."""
import sys
sys.dont_write_bytecode = True
import pandas as pd
import pdh as P, others as O
d1 = P.load('D1')
for e, x in ((55, 20), (20, 10)):
    r = O.turtle(entry=e, exit_=x)
    for a, b in (('2004-06-11', '2026-10-09'), ('2004-06-11', '2015-12-31'), ('2016-01-01', '2026-10-09'), ('2025-05-06', '2026-10-09')):
        O.summary(f'Turtle {e}/{x}', r, a, b)
    print(f'   win rate {(r.pnl>0).mean():.0%}, sizing check: risk per 0.01 lot now ${2*P.wilder_atr(d1,20).iloc[-1]:.0f}')
for a, b in (('2004-06-11', '2026-10-09'), ('2004-06-11', '2015-12-31'), ('2016-01-01', '2026-10-09'), ('2025-05-06', '2026-10-09')):
    x = d1[a:b].close; nd = len(pd.bdate_range(a, b))
    print(f'hold 0.01 lot {a}..{b}: $/day {(x.iloc[-1]-x.iloc[0]-0.4-0.126*(x.index[-1]-x.index[0]).days)/nd:.2f}, worst drop ${(x-x.cummax()).min():.0f}')
