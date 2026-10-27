"""(3b) What P2 did on the largest news bars and on its worst TEST days (summaries only)."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *
m = load_tf('M1'); A = Arr(m); s = A.signal(); d, t = A.run(s)
F = A.feats(3, 240)
rng_ = (m.high - m.low)
news = rng_[(m.tod >= 65)].nlargest(12)
print('largest M1 bars after 01:05 (range) and P2 trades entered within 30 minutes after them:')
for ts, v in news.items():
    j = m.index.get_loc(ts)
    w = t[(t.ei >= j) & (t.ei <= j + 30)]
    op = t[(t.ei < j) & (t.xi >= j)]
    print(f'  {ts} range ${v:5.1f} move {m.close.iloc[j] - m.open.iloc[j]:+6.1f}, close-VWAP {m.close.iloc[j] - F["vw"][j]:+6.1f}: '
          f'open through it {len(op)} ({op.pnl.sum():+.1f}); entered next 30 min {len(w)} trades, sum {w.pnl.sum():+.1f}, worst {w.pnl.min() if len(w) else 0:+.1f}')
print('\nworst TEST days: trade count, long share, sum, $25 stops, day range and open-to-close move')
for dd in d[d.index >= SPLIT].pnl.nsmallest(4).index:
    tt = t[t.entry.dt.normalize() == dd]; mm = m[m.index.normalize() == dd]
    print(f'  {dd.date()}: {len(tt)} trades, long {(tt.dir == 1).mean():.2f}, sum {tt.pnl.sum():+.1f}, stops {(tt.pnl <= -24.99).sum()}, '
          f'day range ${mm.high.max() - mm.low.min():.0f}, open->close {mm.close.iloc[-1] - mm.open.iloc[0]:+.0f}')
print('\nbest TEST days:')
for dd in d[d.index >= SPLIT].pnl.nlargest(3).index:
    tt = t[t.entry.dt.normalize() == dd]; mm = m[m.index.normalize() == dd]
    print(f'  {dd.date()}: {len(tt)} trades, long {(tt.dir == 1).mean():.2f}, sum {tt.pnl.sum():+.1f}, '
          f'day range ${mm.high.max() - mm.low.min():.0f}, open->close {mm.close.iloc[-1] - mm.open.iloc[0]:+.0f}')
# correlation of P2 day P&L with |day open->close| trend
g = m.groupby(m.index.normalize())
oc = (g.close.last() - g.open.first()).abs().reindex(d.index)
for nm, sel in (('TRAIN', d.index < SPLIT), ('TEST', d.index >= SPLIT)):
    print(f'{nm}: corr(day P&L, |open->close|) {np.corrcoef(d.pnl[sel], oc[sel])[0, 1]:+.2f}; '
          f'P2 $/day on the half of days with the larger |open->close| {d.pnl[sel][oc[sel] >= oc[sel].median()].mean():+.2f}, smaller {d.pnl[sel][oc[sel] < oc[sel].median()].mean():+.2f}')
