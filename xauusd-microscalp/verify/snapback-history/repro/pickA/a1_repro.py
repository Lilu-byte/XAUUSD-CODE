"""(1) reproduce pick A from the rule text; cross-check _sim_next with an independent per-trade loop;
compare with the colleague's trade list (computed by their code, read-only import used ONLY for the diff)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/repro/pickA')
from vA import *

d = load_m15(); s, ar = sig_A(d); S = Sim(d)
days, T = S.run(s)
print('signals', int((s != 0).sum()), 'entry-eligible', int(((s != 0) & S.entry_ok()).sum()), 'trades', len(T))
for nm, (lo, hi) in (('TRAIN', TRAIN), ('TEST', TEST)):
    r = per(days, T, lo, hi)
    print(f"{nm}: {r['per_day']:+.3f}/d  {r['trades_day']:.3f} tr/d  win {r['win']:.3f}  {r['per_trade']:+.3f}/tr  days {r['days']} "
          f"trades {r['trades']}  long share {r['long_share']:.3f}  worst day {r['worst_day']:+.2f}  maxDD {r['max_dd']:+.2f}  t {r['tstat']:+.2f}")

# independent per-trade loop (no numba), same rules
o = d.open.values; h = d.high.values; l = d.low.values; c = d.close.values
spr = d.spread_usd.values + 0.05; tod = d.tod.values; last = d.last_of_session.values
day = d.index.normalize().values
ok = S.entry_ok(); n = len(d)
open_pos = []   # (exit_index, ) for max_open accounting
trades = []
for i in range(n - 1):
    open_pos = [x for x in open_pos if x > i]          # positions exiting at bar i close free their slot before bar i's entry
    if s[i] == 0 or not ok[i] or tod[i] < 65 or tod[i] > 22 * 60 + 29 or last[i]: continue
    if len(open_pos) >= 3: continue
    dr = int(s[i])
    e = o[i + 1] + spr[i + 1] if dr == 1 else o[i + 1]
    px = None; xi = None
    for j in range(i + 1, n):
        if day[j] != day[i]:
            px = o[j] if dr == 1 else o[j] + spr[j]; xi = j; break
        if dr == 1:
            if l[j] <= e - 25: px = min(o[j], e - 25) if j > i + 1 else e - 25; xi = j; break
        else:
            if h[j] + spr[j] >= e + 25: px = max(o[j] + spr[j], e + 25) if j > i + 1 else e + 25; xi = j; break
        if j - i >= 4 or tod[j] >= 22 * 60 + 58 or last[j] or j == n - 1:
            px = c[j] if dr == 1 else c[j] + spr[j]; xi = j; break
    pnl = px - e if dr == 1 else e - px
    trades.append((i, dr, pnl, xi)); open_pos.append(xi)
L = pd.DataFrame(trades, columns=['ei', 'dir', 'pnl', 'xi'])
m = T.merge(L, on='ei', how='outer', suffixes=('_sim', '_loop'), indicator=True)
print('loop trades', len(L), 'sim trades', len(T), 'matched', int((m._merge == 'both').sum()),
      'max |pnl diff|', float((m.pnl_sim - m.pnl_loop).abs().max()), 'dir mismatches', int((m.dir_sim != m.dir_loop).sum()))

# colleague's trade list, for the diff only
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-history')
import hlib
dc = hlib.load_tf('M15'); fc = hlib.features(dc, 'M15'); sc = hlib.signal(dc, fc, 2, 4.0, 1)
Sc = hlib.Scorer(dc, 'M15', fc.ar); dC, TC = Sc.run(sc, 4, 25, 3)
print('their signals', int((sc != 0).sum()), 'mine', int((s != 0).sum()), 'signal bar mismatches', int((np.sign(sc) != s).sum()))
mm = T.merge(TC, on='entry', how='outer', suffixes=('_me', '_them'), indicator=True)
print('their trades', len(TC), 'matched', int((mm._merge == 'both').sum()), 'max |pnl diff|', float((mm.pnl_me - mm.pnl_them).abs().max()),
      'sum diff', float(mm.pnl_me.sum() - mm.pnl_them.sum()))
for nm, (lo, hi) in (('TRAIN', TRAIN), ('TEST', TEST)):
    a = hlib.stats(dC, TC, lo, hi)
    print(f"  theirs {nm}: {a['per_day']:+.3f}/d {a['trades_day']:.3f} tr/d days {a['days']}")
T.to_csv('/mnt/project-files/xauusd-microscalp/verify/snapback-history/repro/pickA/pickA_trades.csv', index=False)
