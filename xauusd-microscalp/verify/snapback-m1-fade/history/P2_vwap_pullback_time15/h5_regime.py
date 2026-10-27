"""(1c) Why the ports only work from 2026: intraday 'VWAP-side' drift by quarter on M15 (2022-07..2026-10).
For every M15 bar 01:15-22:15: drift = sign(Close - session VWAP) x (Close[i+4] - Close[i]) (next hour), in units of
ATR16; and the trend-day share = |day open->close| / day range. P2 is a buy-the-dip-above-VWAP / sell-the-rally-below
rule, so it can only pay in quarters where this drift is positive."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *
m = load_tf('M15'); A = Arr(m, 'M15'); F = A.feats(1, 16)
side = np.sign(A.c - F['vw'])
fwd = np.r_[A.c[4:] - A.c[:-4], np.full(4, np.nan)]
sameday = np.r_[A.day[4:] == A.day[:-4], np.zeros(4, bool)]
ok = (A.tod >= 75) & (A.tod <= 1335) & sameday & ~np.isnan(side)
drift = pd.Series(np.where(ok, side * fwd / F['atr'], np.nan), index=m.index)
g = m.groupby(m.index.normalize()); oc = (g.close.last() - g.open.first()).abs(); rg = g.high.max() - g.low.min()
td = (oc / rg)
q = drift.groupby(drift.index.to_period('Q')).mean(); tq = td.groupby(td.index.to_period('Q')).mean()
print('quarter: VWAP-side next-hour drift (ATR units) | trend-day ratio |open->close|/range')
print('  ' + '  '.join(f'{k} {v:+.3f}|{tq[k]:.2f}' for k, v in q.items()))
pre = q[q.index < pd.Period('2026Q1')]; post = q[q.index >= pd.Period('2026Q1')]
print(f'2022Q3-2025Q4: drift > 0 in {(pre > 0).sum()} of {len(pre)} quarters (mean {pre.mean():+.3f}); 2026Q1-Q4: {(post > 0).sum()} of {len(post)} (mean {post.mean():+.3f})')
