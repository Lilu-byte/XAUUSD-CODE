"""POST-HOC transparency only (run after the pick was frozen and scored): test-window and common-window results
of all 28 stage-1 variants, to see whether ANY regime gate helps out of sample. Not used for selection."""
import numpy as np, pandas as pd
from common import *
R = d1_regimes(); rows = []; days, pp, A, B = pair_daily()
for bn in ['MAXI', 'DON']:
    d, sig0, kw = base(bn)
    for lo in [False, True]:
        for rg in ['NONE', 'MA200', 'MOM12', 'MOM6', 'ADX25', 'VOL', 'MA+MOM12']:
            t = simulate(d, gate(d, sig0, rg, lo, R), **kw); P_ = daily(t, d)
            ptr = window_daily(t, d, *TRAIN); pte = window_daily(t, d, *TEST); y = years(P_)
            mine = P_.reindex(days, fill_value=0.0); cw = summarize(pp + mine)
            rows.append(dict(base=bn, dir='long' if lo else 'both', regime=rg, train=round(ptr.mean(), 2), test=round(pte.mean(), 2),
                             test_dd=summarize(pte)['max_dd'], common=round(mine.mean(), 2), w_pair=cw['per_day'], w_pair_dd=cw['max_dd'],
                             w_pair_lm=cw['losing_months'], **{str(k): v for k, v in y.loc[2022:].items()}))
res = pd.DataFrame(rows); pd.set_option('display.width', 250)
print(res.to_string(index=False)); res.to_csv('posthoc_all_test.csv', index=False)
