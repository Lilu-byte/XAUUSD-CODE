"""Common window May 2025..Oct 2026: core (own MTM from reimpl.py) alone and added to the pair.
Pair daily P&L = sum by exit date of the two replay CSVs; trading days = unique dates of the M5 data.
Also: margin / concurrent lots, random-timing test, coin-flip test, execution checks with H1."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, pandas as pd
import gbt

OUT = '/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-long-core/'
core = pd.read_csv(OUT + 'core_daily_mtm.csv', index_col=0, parse_dates=True)
m5 = gbt.load('M5')
days = pd.DatetimeIndex(np.unique(m5.index.normalize()))
print('M5 days', days[0].date(), days[-1].date(), len(days))
print('M5 days not in D1:', [x.date() for x in days.difference(core.index)][:10], ' D1 days in range not in M5:',
      [x.date() for x in core.index[(core.index >= days[0]) & (core.index <= days[-1])].difference(days)][:10])

ga = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
ab = pd.read_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
pair = (ga.groupby(ga.exit_time.dt.normalize()).pnl_usd.sum().reindex(days, fill_value=0)
        + ab.groupby(ab.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0))
c = core.core_mtm.reindex(days).fillna(0.0)    # D1 MTM; a missing D1 day carries 0
h = core.hold.reindex(days).fillna(0.0)
# a D1 bar missing on an M5 date would lose a close-to-close move; check totals
print('core MTM over M5 days', round(c.sum(), 1), ' over D1 days same span',
      round(core.core_mtm[(core.index >= days[0]) & (core.index <= days[-1])].sum(), 1))


def st(p, lab):
    eq = p.cumsum(); mo = p.groupby(p.index.to_period('M')).sum()
    return dict(what=lab, per_day=round(p.mean(), 2), total=round(p.sum(), 0), max_dd=round((eq - eq.cummax()).min(), 0),
                worst_day=round(p.min(), 0), worst_month=round(mo.min(), 0), losing_months=f'{(mo < 0).sum()}/{len(mo)}')

R = pd.DataFrame([st(pair, 'pair'), st(c, 'core MTM'), st(pair + c, 'pair + core MTM'), st(h, 'hold 0.01 MTM'),
                  st(pair + h, 'pair + hold')]).set_index('what')
# booked-by-exit version of the core (misleading view)
tr = pd.read_csv(OUT + 'trades_own.csv', parse_dates=['exit_time'])
cb = tr.dropna(subset=['exit_time']).groupby(tr.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0)
R = pd.concat([R, pd.DataFrame([st(cb, 'core booked by exit'), st(pair + cb, 'pair + core booked')]).set_index('what')])
print(R.to_string())
print('corr(core MTM, pair) daily', round(np.corrcoef(c, pair)[0, 1], 3), ' monthly',
      round(np.corrcoef(c.groupby(c.index.to_period('M')).sum(), pair.groupby(pair.index.to_period('M')).sum())[0, 1], 3))
R.to_csv(OUT + 'common_window.csv')

# ---------- margin: concurrent lots ----------
iv = [(r.entry_time, r.exit_time) for r in ga.itertuples()] + [(r.entry_time, r.exit_time) for r in ab.itertuples()]
core_iv = [(pd.Timestamp(r.entry_time), pd.Timestamp(r.exit_time) if pd.notna(r.exit_time) else pd.Timestamp('2026-12-31'))
           for r in tr.itertuples()]
ev = []
for a, b in iv + core_iv:
    ev += [(a, 1), (b, -1)]
ev.sort(key=lambda x: (x[0], x[1]))
cur = mx = 0; when = None
for t_, k in ev:
    if t_ < pd.Timestamp('2025-05-01'):
        cur += k; continue
    cur += k
    if cur > mx: mx, when = cur, t_
print(f'max concurrent positions (0.01 each) in common window: {mx}  first at {when}')

# ---------- random timing: circular shifts of the position series within the test window ----------
d = gbt.load('D1'); cl = d.close.values
pos = core.pos.reindex(d.index).values
dow = d.index.dayofweek.values
mask = (d.index >= '2022-01-01')
def mtm_of(posv):
    # pos at close of i; trades at open of i when pos changes; same cost model as reimpl.py
    p = np.zeros(len(posv))
    o = d.open.values
    for i in range(1, len(posv)):
        a, b = posv[i - 1], posv[i]
        sw = (3 * 0.126 if dow[i - 1] == 2 else 0.126)
        if a == 0 and b == 1: p[i] = cl[i] - (o[i] + 0.4)
        elif a == 1 and b == 0: p[i] = (o[i] - 0.1) - cl[i - 1] - sw
        elif a == 1: p[i] = cl[i] - cl[i - 1] - sw
    return p
base = mtm_of(pos)[mask].mean()
pw = pos[mask]; rng = np.random.default_rng(7); res = []
for _ in range(1000):
    k = rng.integers(1, len(pw)); sh = np.roll(pw, k)
    full = pos.copy(); full[mask] = sh
    res.append(mtm_of(full)[mask].mean())
res = np.array(res)
print(f'test 2022-26 rule {base:.2f}/day; circular-shift random timing (same in-market %, same run lengths): '
      f'median {np.median(res):.2f}, rule beats {np.mean(base > res)*100:.0f}% of 1000')

# ---------- coin-flip directions on the same entry bars (exit on the down-cross for either side) ----------
f, s = d.close.rolling(50).mean(), d.close.rolling(200).mean()
up = (f > s) & s.notna(); dn = (f <= s) & s.notna()
cross = (up & ~up.shift(1, fill_value=False)).astype(float).values
tt = gbt.simulate(d, cross, exit_long=dn.values, exit_short=dn.values)
print('golden-cross entries via cross bar only:', len(tt), 'trades (should equal 16)')
dt = d[d.index >= '2016-07-29']
ct = (up & ~up.shift(1, fill_value=False))[d.index >= '2016-07-29'].astype(float).values
cf = gbt.coinflip(dt, ct, runs=200, exit_long=dn[d.index >= '2016-07-29'].values, exit_short=dn[d.index >= '2016-07-29'].values)
rule16 = gbt.daily(gbt.simulate(dt, ct, exit_long=dn[d.index >= '2016-07-29'].values), dt).mean()
print(f'2016-07..2026-10 booked $/day: rule {rule16:.2f}, coin-flip median {np.median(cf):.2f}, beats {np.mean(rule16 > cf)*100:.0f}% of 200')

# ---------- execution: fill at 00:00 open vs 02:00 H1 open, and spread at rollover ----------
h1 = gbt.load('H1')
print('\nentry/exit fills 2016+: D1 open vs H1 02:00 open (and H1 00:00/01:00 spread points)')
for r in tr.itertuples():
    for lab, tt_ in [('entry', r.entry_time), ('exit', r.exit_time)]:
        if pd.isna(tt_) or pd.Timestamp(tt_) < pd.Timestamp('2016-08-01'): continue
        day = pd.Timestamp(tt_)
        x = h1[(h1.index >= day) & (h1.index < day + pd.Timedelta(hours=4))]
        o02 = x.open[x.index.hour == 2]
        print(f'  {lab} {day.date()} D1open {d.open.get(day, np.nan):.2f}  H1 first {x.index[0].time()} open {x.open.iloc[0]:.2f} '
              f'spread_pts {int(x.spread.iloc[0])}  02:00 open {o02.iloc[0] if len(o02) else np.nan:.2f}')
