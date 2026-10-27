"""List the failed baskets (force-closed at a loss) of the M5 proxy before the M1 data starts, with that day's price action."""
from common import *
exec(open(VOUT + 'r3_longhist.py').read().split('allrows = []')[0])
d = prep('M5'); gg = G(d); cf = CFG['M5']
kw = dict(first_tod=cf['first_tod'], last_tod=cf['last_tod'], end_tod=cf['end_tod'])
sig = mr_signal(d, look=1, k=1.5, win=48)
D1 = d.groupby(d.index.normalize()).agg(o=('open', 'first'), h=('high', 'max'), l=('low', 'min'), c=('close', 'last'))
for seed in range(3):
    days, bask, eql, levh = gg.run(sig, seed=seed, **kw)
    f = bask[(bask.pnl < 0)]
    print(f'seed {seed}: failed baskets {len(f)}, total {f.pnl.sum():+.0f}; all baskets {len(bask)}; total pnl {days.pnl.sum():+.0f}')
    if seed == 0:
        for _, r in f.iterrows():
            dd = D1.loc[r.start.normalize()]
            print(f'   {r.start} -> {r.end} dir {r.dir:+d} levels {r.levels} pnl {r.pnl:+8.1f} mae {r.mae:+8.1f} why {r.why} | day O {dd.o:.0f} H {dd.h:.0f} L {dd.l:.0f} C {dd.c:.0f} (C-O {dd.c - dd.o:+.0f})')
# monthly P&L for seed 0
days, bask, eql, levh = gg.run(sig, seed=0, **kw)
print(days.pnl.groupby(days.index.to_period('M')).sum().round(0).to_string())
