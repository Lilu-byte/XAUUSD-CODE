"""How much can the M5 history say about P1? (1) Week by week on the M1 period: does the M5 port A (fade 5-min moves,
hold 1 bar) move together with P1? (2) P1's trade count scales with volatility: estimate from the M1 period how many
signals a day P1 would have produced in each earlier quarter (from the M5 mean range), since $7 is an absolute
threshold. (3) TEST concentration and a day-bootstrap p-value for TEST > 0."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history')
from vlib import *
import h1_history as H1

m = load_m1(); A = Arr(m)
s = p1_signal(m); d, t = run(A, s)
x = load_tf('M5'); f = H1.feats(x)
K = H1.calib_K(f, 1, H1.Q_P1)
sa = H1.signal(f, 1, K)
xm = x[x.index >= M1START]; fm = f[f.index >= M1START]; Am = Arr(xm)
da, ta = run(Am, sa[x.index >= M1START], 1000.0, 1000.0, 1, 2, spr=0.0, secs=300, use_spread=False)
wk1 = d.pnl.groupby(d.index.to_period('W')).sum(); wka = da.pnl.groupby(da.index.to_period('W')).sum()
j = pd.concat([wk1, wka], axis=1, keys=['p1', 'm5a']).dropna()
print(f'(1) weekly P1 $ vs M5 port-A gross $ over the M1 period: {len(j)} weeks, correlation {j.p1.corr(j.m5a):+.2f}; '
      f'daily correlation {pd.concat([d.pnl, da.pnl], axis=1).dropna().corr().iloc[0, 1]:+.2f}')
mo = pd.concat([d.pnl.groupby(d.index.to_period('M')).mean(), da.pnl.groupby(da.index.to_period('M')).mean()], axis=1, keys=['P1 $/day', 'M5 A gross $/day'])
print('    by month: ' + '; '.join(f'{k}: P1 {r.iloc[0]:+.2f}, M5A {r.iloc[1]:+.2f}' for k, r in mo.iterrows()))
# (2) signals per day vs daily mean M5 range
okh = (m.tod.values >= 65) & (m.tod.values <= 22 * 60 + 29)
sig_day = pd.Series((s != 0) & okh, index=m.index).groupby(m.index.normalize()).sum()
rng5 = (x.high - x.low).groupby(x.index.normalize()).mean()
z = pd.concat([sig_day, rng5], axis=1, keys=['n', 'r'], sort=True).dropna()
print(f'(2) M1 period: corr(P1 signals/day, mean M5 range of the day) {z.n.corr(z.r):+.2f}; days with >= 60 signals: {(z.n >= 60).sum()}')
# empirical model: the distribution of |r3| / (mean M5 range of the day) on the M1 period is kept; earlier days use their own M5 range
r3 = (m.close - m.close.shift(3)).abs()
day = m.index.normalize()
zz = (r3 / pd.Series(day, index=m.index).map(rng5)).values[okh]
zz = np.sort(zz[~np.isnan(zz)])
nbar = okh.sum() / len(np.unique(day))
def rate(R):                     # share of M1 bars with |r3| > $7 on a day whose mean M5 range is R
    return 1 - np.searchsorted(zz, 7.0 / R) / len(zz)
chk = np.mean([rate(R) for R in z.r]) * nbar
print(f'    model check on the M1 period: {chk:.1f} signals/day predicted vs {z.n.mean():.1f} actual')
est = rng5.groupby(rng5.index.to_period('Q')).apply(lambda v: float(np.mean([rate(R) for R in v.values]) * nbar))
print('    implied P1 signals/day by quarter (from the M5 range): ' + ', '.join(f'{k}: {v:.0f} (M5 range {rng5.groupby(rng5.index.to_period("Q")).mean()[k]:.1f})' for k, v in est.items()))
top = rng5.nlargest(3)
print('    highest-volatility days: ' + ', '.join(f'{k.date()} (M5 range {v:.1f}): {rate(v) * nbar:.0f} signals' for k, v in top.items()) + f'; M1-period max actual {int(z.n.max())}')
# (3) TEST concentration + bootstrap
te = d.pnl[d.index >= SPLIT].sort_values(ascending=False)
rs = np.random.default_rng(11)
bs = np.array([rs.choice(te.values, len(te)).mean() for _ in range(20000)])
tr = d.pnl[d.index < SPLIT]
print(f'(3) TEST {te.mean():+.2f}/day over {len(te)} days; best 3 days {te.iloc[:3].round(1).tolist()} sum {te.iloc[:3].sum():+.1f} vs total {te.sum():+.1f}; '
      f'without them {te.iloc[3:].mean():+.2f}/day; day-bootstrap P(mean <= 0) = {np.mean(bs <= 0):.3f}; P(mean >= 5) = {np.mean(bs >= 5):.3f}; '
      f'TRAIN {tr.mean():+.2f}/day, sd of a day {tr.std():.1f} (TRAIN) / {te.std():.1f} (TEST)')
# (4) P1 day P&L by how busy the day was (signals per day quartile) -- the absolute $7 threshold makes busy days the tail
nd = t.groupby(t.entry.dt.normalize()).size().reindex(d.index, fill_value=0)
qd = pd.qcut(nd, 4, labels=['quietest', 'q2', 'q3', 'busiest'])
g = d.pnl.groupby(qd, observed=True)
print('(4) P1 $/day by quartile of trades per day: ' + '; '.join(
    f'{k}: {nd[qd == k].mean():.0f} tr/d, mean {v.mean():+.1f}, sd {v.std():.1f}, worst {v.min():+.1f}, best {v.max():+.1f}' for k, v in g))
print(f'    sd of day P&L / sqrt(trades): {(d.pnl.std() / np.sqrt(nd.mean())):.2f} per sqrt-trade; '
      f'at the implied 2026Q1 rate (~149 signals/day, ~120 trades with max 2 open) a 1-sd day would be about +-{d.pnl.std() / np.sqrt(nd.mean()) * np.sqrt(120):.0f} dollars')
