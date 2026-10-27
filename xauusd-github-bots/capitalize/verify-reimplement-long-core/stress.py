"""Extra checks on the reimplemented core:
1) look-ahead: recompute every decision on data truncated at that bar; must match the full-data decision
2) swap stress in the test window: doubled swap, and 'Fed funds + 1.5%' financing (approx monthly FF, from memory)
3) fill at the 02:00 server H1 open instead of the D1 open
4) 2026-only slice of pair + core"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd
import gbt

OUT = '/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-long-core/'
d = gbt.load('D1'); cl = d.close; o = d.open.values; dow = d.index.dayofweek.values
f, s = cl.rolling(50).mean(), cl.rolling(200).mean(); up = ((f > s) & s.notna()).values

# 1) truncation test on every bar from 2016 (decision at close of bar i uses only bars <= i)
idx = np.where(d.index >= '2016-01-01')[0]; bad = 0
for i in idx[::5]:
    x = cl.iloc[:i + 1]
    u = x.iloc[-50:].mean() > x.iloc[-200:].mean()
    bad += (u != up[i])
print('truncation test, decisions differing:', bad, 'of', len(idx[::5]))

# position at close of each bar (same as reimpl.py)
pos = np.zeros(len(d))
for i in range(1, len(d)):
    pos[i] = 1.0 if up[i - 1] else 0.0 if (s.iloc[i - 1] == s.iloc[i - 1]) else 0.0

def mtm(posv, swap_night, entry_px=None, exit_px=None):
    p = np.zeros(len(posv)); c = cl.values
    for i in range(1, len(posv)):
        a, b = posv[i - 1], posv[i]
        k = 3.0 if dow[i - 1] == 2 else 1.0
        sw = k * swap_night[i]
        if a == 0 and b == 1:
            e = (entry_px[i] if entry_px is not None else o[i]) + 0.4; p[i] = c[i] - e
        elif a == 1 and b == 0:
            x = (exit_px[i] if exit_px is not None else o[i]) - 0.1; p[i] = x - c[i - 1] - sw
        elif a == 1:
            p[i] = c[i] - c[i - 1] - sw
    return pd.Series(p, index=d.index)

hold = np.ones(len(d)); hold[0] = 0
test = d.index >= '2022-01-01'
base = np.full(len(d), 0.126)
# Fed funds effective, monthly approx (2026 values assumed flat ~3.6%; not known exactly)
ff = {2022: [0.08, 0.08, 0.20, 0.33, 0.77, 1.21, 1.68, 2.33, 2.56, 3.08, 3.78, 4.10],
      2023: [4.33, 4.57, 4.65, 4.83, 5.06, 5.08, 5.12, 5.33, 5.33, 5.33, 5.33, 5.33],
      2024: [5.33] * 8 + [5.13, 4.83, 4.64, 4.48],
      2025: [4.33] * 8 + [4.22, 4.09, 3.88, 3.72],
      2026: [3.64] * 12}
rate = np.array([(ff.get(t.year, [np.nan] * 12)[t.month - 1] + 1.5) / 100 for t in d.index])
fin = np.r_[0.126, rate[1:] / 365 * cl.values[:-1]]     # per-night charge on the previous close
rows = []
for lab, sw in [('swap $0.126 (convention)', base), ('swap x2 $0.252', base * 2), ('Fed funds + 1.5% of price', fin)]:
    r = mtm(pos, sw)[test]; h = mtm(hold, sw)[test]
    rows.append(dict(swap=lab, rule_per_day=round(r.mean(), 2), hold_per_day=round(h.mean(), 2),
                     rule_swap_paid=round(r.sum() - mtm(pos, np.zeros(len(d)))[test].sum(), 0) * -1))
print(pd.DataFrame(rows).to_string(index=False))

# 3) fill at 02:00 server H1 open
h1 = gbt.load('H1'); o2 = h1.open[h1.index.hour == 2]; o2.index = o2.index.normalize()
px2 = o2.reindex(d.index).fillna(d.open).values
r2 = mtm(pos, base, entry_px=px2, exit_px=px2)
print(f'test $/day with 02:00 fills: {r2[test].mean():.2f}  (D1-open fills: {mtm(pos, base)[test].mean():.2f})')

# 4) slices of pair + core
core = pd.read_csv(OUT + 'core_daily_mtm.csv', index_col=0, parse_dates=True)
m5 = gbt.load('M5'); days = pd.DatetimeIndex(np.unique(m5.index.normalize()))
ga = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['exit_time'])
ab = pd.read_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['exit_time'])
pair = (ga.groupby(ga.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0)
        + ab.groupby(ab.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0))
c = core.core_mtm.reindex(days).fillna(0)
for lab, a, b in [('2025-05..2025-12', '2025-05-01', '2025-12-31'), ('2026-01..2026-10', '2026-01-01', '2026-10-31')]:
    k = (days >= a) & (days <= b)
    print(f'{lab}: pair {pair[k].mean():.2f}/day  core {c[k].mean():.2f}/day  pair+core {(pair + c)[k].mean():.2f}/day')
