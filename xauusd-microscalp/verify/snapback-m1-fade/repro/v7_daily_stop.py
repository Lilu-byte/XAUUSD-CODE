"""EA default daily stop ($15 closed loss -> no new entries that day), re-implemented from the rule in ea_replica.daily_stop."""
from common import *
R = Rep(); m = R.m
days, T = R.run(entry_filter(m, raw_signal(m.close.values)))
keep = []
for d, g in T.groupby(T.entry.dt.normalize()):
    cum = 0.0; halt_bar = None
    for xi, p in sorted(zip(g.xi, g.pnl)):
        cum += p
        if cum <= -15.0: halt_bar = xi; break
    keep.append(g if halt_bar is None else g[g.ei < halt_bar])
K = pd.concat(keep)
dK = K.groupby(K.entry.dt.normalize()).pnl.sum().reindex(R.dates, fill_value=0.0)
for p in ('train', 'test'): print(fmt(f'daily stop 15 {p}', stats(dK, K, p)))
