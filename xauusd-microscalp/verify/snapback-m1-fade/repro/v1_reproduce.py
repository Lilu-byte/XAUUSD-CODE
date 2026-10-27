"""(1) Reproduce P1 from the rule text with the shared next-bar-open simulator and with an independent python simulator.
Compare trade lists against the family's TEST trade list."""
import json
from common import *

R = Rep(); m = R.m; H = R.H
raw = raw_signal(m.close.values)
s = entry_filter(m, raw)
print('raw signal bars', int((raw != 0).sum()), ' after EA entry filter', int((s != 0).sum()))
days, T = R.run(s)
res = {}
for per in ('train', 'A', 'B', 'test'):
    r = stats(days, T, per); res[per] = r
    print(fmt(f'shared _sim_next {per}', r))

# independent python simulator
t_ns = m.index.values.astype(np.int64)
out = sim_py(H.o, H.h, H.l, H.c, t_ns, R.spr('base'), H.tod, H.day, H.last, s)
P = pd.DataFrame(out, columns=['ei', 'xi', 'dir', 'pnl'])
P['entry'] = m.index[P.ei.values]
dP = P.groupby(P.entry.dt.normalize()).pnl.sum().reindex(R.dates, fill_value=0.0)
for per in ('train', 'test'):
    print(fmt(f'independent sim_py {per}', stats(dP, P, per)))
a = T.sort_values(['ei', 'dir']).reset_index(drop=True); b = P.sort_values(['ei', 'dir']).reset_index(drop=True)
same = len(a) == len(b) and (a.ei.values == b.ei.values).all()
print('trade count shared vs python', len(a), len(b), 'same entry bars', same,
      'max |pnl diff|', float(np.abs(a.pnl.values - b.pnl.values).max()) if same else 'n/a')

# compare to the family's TEST trades
fam = pd.read_csv('/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade/final_test_trades_P1_snap_time3.csv', parse_dates=['entry'])
mine = T[T.entry >= SPLIT]
mm = mine.merge(fam, on=['entry', 'dir'], how='outer', indicator=True, suffixes=('', '_f'))
print('family TEST trades', len(fam), 'mine', len(mine), 'matched', int((mm._merge == 'both').sum()),
      'only mine', int((mm._merge == 'left_only').sum()), 'only family', int((mm._merge == 'right_only').sum()))
both = mm[mm._merge == 'both']
print('max |pnl diff| on matched', float(np.abs(both.pnl - both.pnl_f).max()))
json.dump({k: {a: float(b) for a, b in v.items()} for k, v in res.items()}, open(OUT + 'v1_reproduce.json', 'w'), indent=1)
T.to_csv(OUT + 'trades_base.csv', index=False)
