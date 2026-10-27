"""Coin-flip, common window with the pair, margin overlap, parameter neighbourhood (post-hoc, info only)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-regime-breakout')
from indep import load, indicators, run, daily

h = load('/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv'); d1 = load('/mnt/project-files/xauusd-price-action/data/XAUUSD_D1.csv')
alld = pd.DatetimeIndex(np.unique(h.index.normalize()))
tr_days = alld[alld < '2022-01-01']; te_days = alld[alld >= '2022-01-01']
ind = indicators(h, d1)
t, _ = run(h, ind)
pick_test = daily(t, te_days).mean()

# ---- coin flip on the same signal bars (direction random per bar, same exit/stop rules)
c = ind['c']; reg = ind['reg']
sigbars = ((c > ind['hh']) & (reg > 0)) | ((c < ind['ll']) & (reg < 0))
rng = np.random.default_rng(7); res_te = []; res_tr = []
for r in range(100):
    s = np.zeros(len(c)); s[sigbars] = np.where(rng.random(sigbars.sum()) < .5, 1, -1)
    tr_, _ = run(h, ind, sig=s)
    res_te.append(daily(tr_, te_days).mean()); res_tr.append(daily(tr_, tr_days).mean())
res_te = np.array(res_te); res_tr = np.array(res_tr)
print(f'coin-flip test: median {np.median(res_te):.2f}, pick {pick_test:.2f} beats {np.mean(pick_test > res_te) * 100:.0f}% of 100 runs')
print(f'coin-flip train: median {np.median(res_tr):.2f}, pick {daily(t, tr_days).mean():.2f} beats {np.mean(daily(t, tr_days).mean() > res_tr) * 100:.0f}%')

# ---- common window with the pair
m5 = pd.read_csv('/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv', usecols=['time'])
cdays = pd.DatetimeIndex(np.unique(pd.to_datetime(m5.time, format='%Y.%m.%d %H:%M').dt.normalize()))
cdays = cdays[(cdays >= '2025-05-01')]
aa = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
ab = pd.read_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
pa = aa.groupby(aa.exit_time.dt.normalize()).pnl_usd.sum().reindex(cdays, fill_value=0)
pb = ab.groupby(ab.exit_time.dt.normalize()).pnl.sum().reindex(cdays, fill_value=0)
pair = pa + pb
pk = daily(t, cdays)
print('common days', len(cdays), cdays[0].date(), cdays[-1].date(), '| pick trades in window', int(((t.exit_time >= cdays[0])).sum()))
def st(p, lab):
    eq = p.cumsum(); m = p.groupby(p.index.to_period('M')).sum()
    print(f'{lab:12s} $/day {p.mean():6.2f}  total {p.sum():7.0f}  maxDD {(eq - eq.cummax()).min():6.0f}  losing months {(m < 0).sum()}/{len(m)}  ret/DD {p.sum() / -(eq - eq.cummax()).min():.1f}')
st(pair, 'pair'); st(pk, 'pick alone'); st(pair + pk, 'pair + pick')
print('daily corr pick vs pair', round(np.corrcoef(pk, pair)[0, 1], 3),
      ' weekly', round(np.corrcoef(pk.resample('W').sum(), pair.resample('W').sum())[0, 1], 3))
pkm = pk.groupby(pk.index.to_period('M')).sum(); print('pick by month in window:', pkm.round(0).astype(int).to_dict())
p25 = pk[pk.index.year == 2025].mean(); p26 = pk[pk.index.year == 2026].mean()
print(f'pick in window: 2025 part {p25:.2f}/day, 2026 part {p26:.2f}/day')
# hold over common window
hw = h.loc['2025-05-01':]
print('hold common window gross $/day', round((hw.close.iloc[-1] - hw.open.iloc[0]) / len(cdays), 2))

# ---- margin: overlapping open positions (pick exit time = end of exit bar, conservative)
iv = [(r.entry_time, r.exit_time) for r in aa.itertuples()] + [(r.entry_time, r.exit_time) for r in ab.itertuples()] + \
     [(r.entry_time, r.exit_time + pd.Timedelta(hours=1)) for r in t[t.exit_time >= '2025-05-01'].itertuples()]
ev = sorted([(a, 1) for a, b in iv] + [(b, -1) for a, b in iv], key=lambda x: (x[0], x[1]))
cur = mx = 0; tmax = None; dur = pd.Timedelta(0); last = None
for tm, dlt in ev:
    if cur >= 3 and last is not None: dur += tm - last
    cur += dlt; last = tm
    if cur > mx: mx = cur; tmax = tm
print('max simultaneous 0.01 positions (pair + pick):', mx, 'first at', tmax, '| time at 3 open:', dur)

# ---- parameter neighbourhood, post-hoc on both windows (information only, not a re-pick)
rows = []
for mom in (63, 100, 126, 150, 189, 252):
    for ent, ex in ((100, 50), (120, 60), (140, 70), (120, 40), (120, 80)):
        for sm in (2.0, 2.5, 3.0):
            ii = indicators(h, d1, mom_n=mom, ent=ent, ex=ex)
            tt, _ = run(h, ii, stop_mult=sm)
            rows.append(dict(mom=mom, ent=ent, ex=ex, stop=sm, train=daily(tt, tr_days).mean(), test=daily(tt, te_days).mean()))
g = pd.DataFrame(rows)
g.round(3).to_csv('/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-regime-breakout/neighbourhood.csv', index=False)
print('neighbourhood (90 combos): train>0 in', (g.train > 0).sum(), '| test>0 in', (g.test > 0).sum(),
      '| test > hold 1.74 in', (g.test > 1.74).sum(), '| test median', round(g.test.median(), 2), 'range', round(g.test.min(), 2), round(g.test.max(), 2))
print('train-best in neighbourhood:', g.loc[g.train.idxmax()].round(3).to_dict())
print(g[(g.ent == 120) & (g.ex == 60) & (g.stop == 2.5)].round(3).to_string(index=False))
