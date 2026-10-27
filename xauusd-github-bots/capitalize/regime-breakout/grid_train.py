"""Stage 1: choose on TRAIN ONLY (2016-07-29 .. 2021-12-31). Test-period results are not computed here.
Grid (fixed before running): base {MAXI, DON} x direction {both, long-only} x regime
{NONE, MA200, MOM12, MOM6, ADX25, VOL, MA+MOM12} = 28 variants.
Selection rule (fixed before running): highest train $/day among variants with >= 15 trades/year;
tie-break: fewer losing train years (2017-2021 full years)."""
import numpy as np, pandas as pd
from common import *
R = d1_regimes(); rows = []
for bn in ['MAXI', 'DON']:
    d, sig0, kw = base(bn)
    for lo in [False, True]:
        for rg in ['NONE', 'MA200', 'MOM12', 'MOM6', 'ADX25', 'VOL', 'MA+MOM12']:
            sig = gate(d, sig0, rg, lo, R)
            t = simulate(d, sig, **kw)
            p = window_daily(t, d, *TRAIN); tt = trades_in(t, *TRAIN)
            s = summarize(p, tt); y = years(p)
            ny = len(p) / 260.0
            rows.append(dict(base=bn, dir='long' if lo else 'both', regime=rg, per_day=s['per_day'], trades_yr=round(len(tt) / ny, 1),
                             win=s['win'], pf=s['pf'], max_dd=s['max_dd'], lose_yrs=int((y.loc[2017:2021] < 0).sum()),
                             **{str(k): v for k, v in y.items()}))
res = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(res.to_string(index=False))
res.to_csv('grid_train.csv', index=False)
ok = res[res.trades_yr >= 15].sort_values(['per_day', 'lose_yrs'], ascending=[False, True])
print('\nTop by rule:\n', ok.head(6).to_string(index=False))
