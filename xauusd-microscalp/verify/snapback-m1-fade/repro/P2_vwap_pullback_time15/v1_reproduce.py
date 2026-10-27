"""(1) Reproduce TRAIN / TEST $/day of P2 from my own signal code, shared _sim_next and my independent pysim."""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/repro/P2_vwap_pullback_time15')
from p2lib import *
R = Rep(); m = R.m
raw, atr, vw, r3 = signal_df(m)
s = entry_filter(m, raw)
print('raw signal bars', int((raw != 0).sum()), 'after EA entry filter', int((s != 0).sum()),
      'TRAIN/TEST raw', int((raw[m.index < SPLIT] != 0).sum()), int((raw[m.index >= SPLIT] != 0).sum()))
d, T = R.run(s)
res = {}
for per in ('train', 'A', 'B', 'test'):
    r = stats(d, T, per); res[per] = r; print(fmt('shared _sim_next ' + per, r))
d2, T2 = pysim_frame(R, s)
for per in ('train', 'test'):
    print(fmt('independent pysim ' + per, stats(d2, T2, per)))
a = T.sort_values(['ei', 'xi']).reset_index(drop=True)
print('trade count shared vs pysim', len(a), len(T2), 'same entry bars', np.array_equal(a.ei.values, T2.ei.values),
      'max |pnl diff|', float(np.abs(a.pnl.values - T2.pnl.values).max()) if len(a) == len(T2) else 'n/a')
F = pd.read_csv('/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade/final_test_trades_P2_vwap_pullback_time15.csv',
                parse_dates=['entry'])
mine = T[T.entry >= SPLIT].copy()
key_f = set(zip(F.entry, F.dir)); key_m = set(zip(mine.entry, mine.dir))
j = mine.merge(F, on=['entry', 'dir'], suffixes=('', '_f'))
print('family TEST trades', len(F), 'mine', len(mine), 'matched', len(j), 'only mine', len(key_m - key_f), 'only family', len(key_f - key_m),
      'max |pnl diff| matched', float(np.abs(j.pnl - j.pnl_f).max()) if len(j) else 'n/a')
# variant: spread gate on the RAW recorded spread (zeros pass), as an EA would see the real running min on those bars
raw_b, *_ = signal(m.open.values, m.high.values, m.low.values, m.close.values, m.tick_volume.values.astype(float),
                   m.index.normalize().values, m.spread.values * 0.01)
db, Tb = R.run(entry_filter(m, raw_b))
print(fmt('gate on raw recorded spread train', stats(db, Tb, 'train')))
print(fmt('gate on raw recorded spread test', stats(db, Tb, 'test')))
json.dump(res, open(OUT + 'v1_reproduce.json', 'w'), indent=1, default=float)
T.to_csv(OUT + 'trades_base.csv', index=False)
