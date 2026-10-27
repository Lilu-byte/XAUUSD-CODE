"""Stage 2 (TRAIN ONLY): for the stage-1 pick (DON both, MOM6) try one extra exit rule:
close the trade when the D1 6-month momentum no longer agrees with it. Keep it only if train $/day improves."""
import numpy as np, pandas as pd
from common import *
R = d1_regimes(); d, sig0, kw = base('DON'); sig = gate(d, sig0, 'MOM6', False, R)
g = np.nan_to_num(htf(d, 'D1', R['MOM6'].values))
for flip in [False, True]:
    k = dict(kw)
    if flip:
        k['exit_long'] = kw['exit_long'] | (g <= 0); k['exit_short'] = kw['exit_short'] | (g >= 0)
    t = simulate(d, sig, **k); p = window_daily(t, d, *TRAIN); tt = trades_in(t, *TRAIN)
    print('regime-flip exit' if flip else 'channel exit only', summarize(p, tt), years(p).to_dict())
