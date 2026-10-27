"""Fill-free edge table on TRAIN only (mlib v2 data): average favourable bid move over 1..30 M1 bars per signal vs
the spread paid, plus spread-gated versions and the inner split (Jul flat month / Aug up-trend month)."""
from sigs2 import *
import warnings; warnings.filterwarnings('ignore')

m1 = load_m1(); S = build(m1)
tr = m1.index < SPLIT; mt = m1[tr]
HZ = (1, 2, 3, 5, 10, 20, 30)
rows = []
for k, v in S.items():
    for g in (None, 0.10, 0.15):
        s = (v if g is None else gate(v, m1, g))[tr]
        e = edge(mt, s, horizons=HZ).loc['train']
        r = dict(sig=k, gate=g if g else 'none', **e.to_dict())
        for nm, sel in (('jul', mt.index < HALF), ('aug', mt.index >= HALF)):
            ss = np.where(sel, s, 0)
            r[f'm10_{nm}'] = edge(mt, ss, horizons=(10,)).loc['train', 'move_10m']
        rows.append(r)
R = pd.DataFrame(rows)
R.to_csv(OUT + 'edge2_train.csv', index=False)
pd.set_option('display.width', 250)
cols = ['sig', 'gate', 'signals_day', 'avg_spread'] + [f'move_{k}m' for k in HZ] + ['m10_jul', 'm10_aug']
print(R[cols].round(3).to_string(index=False))
