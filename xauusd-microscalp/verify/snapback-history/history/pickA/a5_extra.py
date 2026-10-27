"""Step 5: side split with t-stats per period, dependence on single events, recent months, news-day examples."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickA')
from alib import *
d = finish(read('M15')); E = Eng(d, 15); s = signal(d, features(d, 15))
days, T = E.run(s, 4, 25, 3)
P = {'TRAIN': ('2022-07-01', '2025-01-01'), 'TEST': ('2025-01-01', None), 'TEST_PRE_M1': ('2025-01-01', '2026-06-26'), 'M1ERA': ('2026-06-26', None)}
for p, (lo, hi) in P.items():
    tt = T[(T.entry >= lo) & ((T.entry < hi) if hi else True)]
    out = []
    for nm, g in (('long (fade down-moves)', tt[tt.dir == 1]), ('short (fade up-moves)', tt[tt.dir == -1])):
        t = g.pnl.mean() / (g.pnl.std(ddof=1) / np.sqrt(len(g)))
        out.append(f"{nm}: n {len(g)} {g.pnl.mean():+.2f}/tr t {t:+.2f}")
    print(f'{p:12s} ' + ' | '.join(out))
te = days[days.index >= '2025-01-01'].pnl
best_day = te.idxmax()
print(f"TEST best day {best_day.date()} {te.max():+.1f}; TEST $/day {te.mean():+.3f}, without that day {te.drop(best_day).mean():+.3f}, "
      f"without the best 3 days {te.drop(te.nlargest(3).index).mean():+.3f}, without the best 5 days {te.drop(te.nlargest(5).index).mean():+.3f}")
tr = days[(days.index >= '2022-07-01') & (days.index < '2025-01-01')].pnl
print(f"TRAIN $/day {tr.mean():+.3f}, without the best 3 days {tr.drop(tr.nlargest(3).index).mean():+.3f}, without the best 5 {tr.drop(tr.nlargest(5).index).mean():+.3f}")
mn = days.pnl.groupby(days.index.to_period('M')).sum()
print('last 12 months $ (month total): ' + ' '.join(f'{i}:{v:+.0f}' for i, v in mn.iloc[-12:].items()))
for dte in ('2026-01-29', '2026-09-04', '2026-08-19', '2026-07-02'):
    g = T[T.entry.dt.normalize() == pd.Timestamp(dte)]
    print(f"{dte}: day {days.pnl.get(pd.Timestamp(dte), 0):+.1f}; trades " + '; '.join(f"{r.entry:%H:%M} {'L' if r.dir == 1 else 'S'} {r.pnl:+.1f}" for _, r in g.iterrows()))
# cost sensitivity: extra cost per trade at which each period breaks even, and with +$0.07 commission and +$1.58 stop slippage
for p, (lo, hi) in P.items():
    tt = T[(T.entry >= lo) & ((T.entry < hi) if hi else True)]
    stp = (tt.pnl <= -24.5).sum()
    adj = tt.pnl.sum() - 0.07 * len(tt) - 1.58 * stp
    nd = ((days.index >= lo) & ((days.index < hi) if hi else True)).sum()
    print(f"{p}: break-even extra cost/trade {tt.pnl.mean():+.2f}; with commission $0.07 and M1-measured stop slippage $1.58 x {stp} stops: {adj / nd:+.2f}/day")
