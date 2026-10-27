"""Look-ahead check: rebuild every feature with ALL input files truncated at time T (M1 bars opening
before T; HTF bars opening before T, i.e. the last one is still forming) and compare with the full
build on M1 rows that close by T. Any difference means a feature peeks at the future."""
import warnings; warnings.filterwarnings('ignore')
import features as F
from features import *
import mlib

full = F.build(); full_cache = F.CACHE
orig_load, orig_m1 = F.load, F.load_m1
bad = 0
for T in ('2026-07-15 16:37', '2026-08-20 10:02', '2026-09-10 17:44'):
    T = pd.Timestamp(T)
    F.load = lambda tf, T=T: orig_load(tf)[lambda d: d.index < T]
    F.load_m1 = lambda T=T: orig_m1()[lambda d: d.index < T]
    F.CACHE = full_cache + '.tmp'
    part = F.build()
    a = full[full.index < T]; b = part.reindex(a.index)
    diff = ((a - b).abs() > 1e-6) & ~(a.isna() & b.isna())
    nd = diff.sum()
    print(T, 'rows', len(a), 'columns with differences:', nd[nd > 0].to_dict())
    bad += nd.sum()
import os; os.remove(F.CACHE)
print('TOTAL differing cells', bad)
