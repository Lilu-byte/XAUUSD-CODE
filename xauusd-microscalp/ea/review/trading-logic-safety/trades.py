import sys; sys.path.insert(0,'/mnt/project-files/xauusd-microscalp/code')
from mlib import *
m = load_m1()
T = pd.read_csv('/mnt/project-files/xauusd-microscalp/ea/expected_trades.csv', parse_dates=['entry'])
T['ei'] = m.index.get_indexer(T.entry); assert (T.ei >= 0).all()
T['xi'] = T.ei + T.bars
T['day'] = T.entry.dt.normalize()
DEF = {'PB': (1.0, 5.0, 20, 3), 'SF': (0.5, 5.0, 5, 1), 'QB': (0.5, 2.0, 5, 1), 'CP': (0.5, 3.0, 5, 3)}
print(T.groupby('module').size())
A = T[T.module.isin(['PB','SF','QB'])].copy()
# 1) shared daily closed loss limit of $15 (EA default) - replica has none
kept = []; halted_days = {}
for d, g in A.groupby('day'):
    ex = g.sort_values('xi'); en = g.sort_values('ei')
    # find first bar at which cumulative closed pnl <= -15
    cum = 0; hb = None
    for xi, p in zip(ex.xi, ex.pnl):
        cum += p
        if cum <= -15: hb = xi; break
    if hb is None: kept.append(g); continue
    k = g[g.ei < hb]   # entries on the halting bar are blocked (exits processed first)
    halted_days[d] = (len(g) - len(k), g.pnl.sum(), k.pnl.sum())
    kept.append(k)
K = pd.concat(kept)
print('days halted by -15:', len(halted_days), 'of', A.day.nunique())
for d, v in halted_days.items(): print(' ', d.date(), 'trades dropped', v[0], 'replica day pnl %+.2f -> with limit %+.2f' % (v[1], v[2]))
for per, sel in (('TRAIN', lambda x: x.day < SPLIT), ('TEST', lambda x: x.day >= SPLIT)):
    a = A[sel(A)]; k = K[sel(K)]; nd = a.day.nunique()
    print(per, 'replica %+.2f/day' % (a.pnl.sum()/nd), 'with -15 limit %+.2f/day' % (k.pnl.sum()/nd), 'trades', len(a), len(k))
# 2) slot freed by timeout on the same bar as the next entry (EA seconds-based hold may still count it)
risk = 0; rows = []
for mod, g in A.groupby('module'):
    tp, sl, to, mo = DEF[mod]
    timed = g[g.bars == to]
    xs = set(timed.xi)
    hit = g[g.ei.isin(xs)]
    # only matters when the module was at its cap at that bar
    for _, r in hit.iterrows():
        openn = ((g.ei < r.ei) & (g.xi >= r.ei)).sum()   # positions open going into bar (incl. ones exiting this bar)
        if openn >= mo: rows.append((mod, r.entry, openn))
print('entries that reuse a slot freed by a timeout exit on the same bar (cap binding):')
R = pd.DataFrame(rows, columns=['mod','entry','open_before'])
print(R.groupby('mod').size(), 'of', A.groupby('module').size().to_dict())
# 3) trades whose exit was forced by session end (last bar / early close)
last = m.last_of_session.values
A['exit_last'] = last[A.xi.values]
A['exit_t'] = m.index[A.xi.values]
print('trades closed on a last-of-session bar:'); print(A[A.exit_last][['entry','module','dir','pnl','bars','exit_t']])
# 4) spread at signal bar and next bar (points)
sp = m.spread.values
A['sp0'] = sp[A.ei.values]; A['sp1'] = sp[np.minimum(A.ei.values+1, len(sp)-1)]
print('entries with recorded spread > 50 pts on signal bar:', (A.sp0 > 50).sum(), ' on next bar:', (A.sp1 > 50).sum(), 'of', len(A))
print(A[(A.sp1 > 50)][['entry','module','pnl','sp0','sp1']].head(20))
