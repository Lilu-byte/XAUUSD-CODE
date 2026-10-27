"""Look-ahead / data / cost hunting around the independent reimplementation."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-regime-breakout')
from indep import load, indicators, run, daily, summ

h = load('/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv'); d1 = load('/mnt/project-files/xauusd-price-action/data/XAUUSD_D1.csv')
alld = pd.DatetimeIndex(np.unique(h.index.normalize()))
tr_days = alld[alld < '2022-01-01']; te_days = alld[alld >= '2022-01-01']
def pd_(t):
    return round(daily(t, tr_days).mean(), 3), round(daily(t, te_days).mean(), 3)

# --- data integrity
print('H1 duplicates', h.index.duplicated().sum(), 'non-monotonic', (np.diff(h.index.values).astype('int64') <= 0).sum())
gap = pd.Series(h.index[1:] - h.index[:-1], index=h.index[1:])
big = gap[gap > pd.Timedelta(hours=3)]
wk = big[~((big.index.dayofweek == 0) & (big < pd.Timedelta(days=3)))]
print('H1 gaps >3h that are not weekends:', len(wk)); print(wk.sort_values().tail(8))
# D1 vs H1 aggregation (same server-time day?)
agg = h.groupby(h.index.normalize()).agg(o=('open', 'first'), hi=('high', 'max'), lo=('low', 'min'), c=('close', 'last'))
j = d1.join(agg, how='inner')
for a, b in (('open', 'o'), ('high', 'hi'), ('low', 'lo'), ('close', 'c')):
    e = (j[a] - j[b]).abs()
    print(f'D1 {a} vs H1-agg: mean abs diff {e.mean():.3f}, >1$ on {int((e > 1).sum())} of {len(e)} days')
print('D1 days missing from H1:', len(d1.loc['2016-07-30':].index.difference(agg.index)), ' H1 days missing from D1:', len(agg.index.difference(d1.index)))

# --- regime timing variants
for mode in ('prevdate', 'close_time', 'sameday_lookahead'):
    ind = indicators(h, d1, d1_mode=mode); t, _ = run(h, ind)
    print(f'D1 mode {mode:18s} train/test $/day', pd_(t), 'trades', len(t))
# regime from H1-aggregated daily closes (independent of the D1 file)
d1h = agg.rename(columns={'o': 'open', 'hi': 'high', 'lo': 'low', 'c': 'close'})
# need 126 days before 2016-07-29: splice D1 file before H1 start
d1s = pd.concat([d1[d1.index < d1h.index[0]], d1h])
ind = indicators(h, d1s); t, _ = run(h, ind); print('regime from H1-built daily closes   ', pd_(t))

# --- ungated / one-sided, same engine
ind = indicators(h, d1)
for lab, kw in (('ungated both', dict(gate=False)), ('gated long only', dict(allow_short=False)),
                ('gated short only', dict(allow_long=False)), ('ungated long only', dict(gate=False, allow_short=False)),
                ('pick, no close&reverse on same open', dict(reverse_same_bar=False))):
    t, _ = run(h, ind, **kw); print(f'{lab:38s}', pd_(t), 'trades', len(t))

# --- costs
for lab, kw in (('swap x2', dict(swap_mult=2)), ('swap x4', dict(swap_mult=4)), ('spread 0.50 slip 0.20', dict(spread=0.5, slip=0.2)),
                ('zero cost', dict(spread=0, slip=0, swap_mult=0))):
    t, _ = run(h, ind, **kw); print(f'{lab:38s}', pd_(t))
t, _ = run(h, ind)
print('test swap total', round(t[t.exit_time >= '2022'].swap.sum(), 1), ' avg nights/trade', round(t.nights.mean(), 2),
      ' avg hold hours', round(((t.exit_time - t.entry_time).dt.total_seconds() / 3600).mean(), 1))
print('exit reasons test', t[t.exit_time >= '2022'].why.value_counts().to_dict())
tt = t[t.exit_time >= '2022']
print('test top-5 trades share of total:', round(tt.pnl.nlargest(5).sum(), 0), 'of', round(tt.pnl.sum(), 0))
print('test top-10 trades:', round(tt.pnl.nlargest(10).sum(), 0))
print('worst trades test:'); print(tt.nsmallest(4, 'pnl')[['entry_time', 'exit_time', 'dir', 'entry', 'exit', 'pnl', 'why']].to_string())
# stop gaps: how many stops filled beyond their level
st = t[t.why == 'stop']
print('stop exits', len(st))

# --- buy and hold test with swap
hs = h.loc['2022-01-01':]
nights = 0
td = np.unique(hs.index.normalize())
for k in range(1, len(td)):
    nights += 3 if pd.Timestamp(td[k - 1]).dayofweek == 2 else 1
gross = hs.close.iloc[-1] - (hs.open.iloc[0] + 0.3)
print('hold test: gross', round(gross, 1), 'swap', round(nights * 0.126, 1), '$/day', round((gross - nights * 0.126) / len(te_days), 3))
hs = h.loc[:'2021-12-31']
print('hold train gross $/day', round((hs.close.iloc[-1] - hs.open.iloc[0]) / len(tr_days), 3))
