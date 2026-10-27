"""Fill-free edge table on TRAIN only: avg favourable move over 1..30 min vs spread paid, per signal,
plus spread-gated versions. Printed rows only (TEST never computed: the M1 frame is cut at SPLIT)."""
from sigs import *
import os
REP = os.environ.get('REPAIR', '1') == '1'   # repaired early-July spreads (default)
SUF = '_rep' if REP else '_orig'
import warnings; warnings.filterwarnings('ignore')

m1 = repaired_m1() if REP else load_m1(); S = build(m1)
tr = m1.index < SPLIT; mt = m1[tr]
rows = []
for k, v in S.items():
    for g in (None, 0.10, 0.15, 0.20):
        s = v[tr] if g is None else gate(v, m1, g)[tr]
        e = edge(mt, s, horizons=(1, 2, 3, 5, 10, 20, 30)).loc['train']
        r = dict(sig=k, gate=g if g else 'none', **e.to_dict())
        rows.append(r)
R = pd.DataFrame(rows)
R.to_csv(OUT + f'edge_train{SUF}.csv', index=False)
pd.set_option('display.width', 250)
cols = ['sig', 'gate', 'signals_day', 'avg_spread'] + [f'move_{k}m' for k in (1, 2, 3, 5, 10, 20, 30)] + ['hit_1m', 'hit_5m']
print(R[cols].round(3).to_string(index=False))
