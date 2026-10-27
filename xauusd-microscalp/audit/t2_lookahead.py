"""Look-ahead checks for htf_on_m1() and forming(), plus day-boundary behaviour on the real data."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd
import mlib

m1 = mlib.load_m1()

# ---- htf_on_m1: value of the H1 bar opened at 10:00 must first appear on M1 row 10:59 (close 11:00)
h1 = mlib.resample(m1, 60)
vals = np.arange(len(h1), dtype=float)          # value = position of the H1 bar
mapped = mlib.htf_on_m1(m1, h1, 'H1', vals)
day = '2026-08-12'
k = h1.index.get_loc(pd.Timestamp(f'{day} 10:00'))
rows = mapped[f'{day} 10:55':f'{day} 11:02']
print('H1 bar 10:00 has value', k)
print(pd.DataFrame({'m1_close_time': rows.index + pd.Timedelta(minutes=1), 'mapped': rows.values}).to_string())
first = mapped[mapped == k].index[0]
print('first M1 row carrying the 10:00 H1 value:', first, '(closes at', first + pd.Timedelta(minutes=1), ')')
# global check: for every M1 row, the mapped H1 bar's close time <= that row's close time
pos = mapped.values
ok = ~np.isnan(pos)
hclose = h1.index[pos[ok].astype(int)] + pd.Timedelta(minutes=60)
m1close = m1.index[ok] + pd.Timedelta(minutes=1)
print('violations (H1 close after M1 close):', int((hclose > m1close).sum()), 'of', ok.sum())
# and freshest possible: mapped bar is the latest H1 bar with close <= M1 close
latest = h1.index.searchsorted(m1close - pd.Timedelta(minutes=60), side='right') - 1
print('rows not using the freshest closed H1 bar:', int((latest != pos[ok].astype(int)).sum()))
# same for M5/H4/D1 built by resample
for tf, mins in (('M5', 5), ('M15', 15), ('H4', 240), ('D1', 1440)):
    hi = mlib.resample(m1, mins)
    mp = mlib.htf_on_m1(m1, hi, tf, np.arange(len(hi), dtype=float)).values
    ok = ~np.isnan(mp)
    hc = hi.index[mp[ok].astype(int)] + pd.Timedelta(minutes=mins)
    mc = m1.index[ok] + pd.Timedelta(minutes=1)
    print(f'{tf}: violations {int((hc > mc).sum())}, NaN rows {int((~ok).sum())}')

# resample(): last H1 bar of a day 22:00 includes 22:00..22:59 -> fine. Partial bins?
cnt = m1.close.resample('60min', label='left', closed='left').count()
cnt = cnt[cnt > 0]
print('H1 bins with <60 M1 bars:', int((cnt < 60).sum()), 'of', len(cnt), '; examples:', cnt[cnt < 60].head(3).to_dict())
cnt4 = m1.close.resample('240min', label='left', closed='left').count(); cnt4 = cnt4[cnt4 > 0]
print('H4 bin starts:', sorted(set(cnt4.index.strftime('%H:%M'))))

# ---- forming(): values at row t must not depend on rows after t
f = mlib.forming(m1, 5)
cut = 5000 + 2      # cut in the middle of a 5-minute group
f2 = mlib.forming(m1.iloc[:cut], 5)
print('forming() identical when future rows removed:', bool(np.allclose(f.iloc[:cut].values, f2.values, equal_nan=True)))
# manual recomputation
g = m1.index.floor('5min')
man_hi = m1.high.groupby(g).cummax(); man_lo = m1.low.groupby(g).cummin()
man_open = m1.open.groupby(g).transform('first')
print('forming f_high/f_low/f_open match manual:', bool(np.allclose(f.f_high, man_hi) and np.allclose(f.f_low, man_lo) and np.allclose(f.f_open, man_open)))
print('f_minute equals (minute % 5)+1 on', float((f.f_minute == (m1.index.minute % 5) + 1).mean()), 'of rows')
# perturbation test: change the future M1 rows inside the group and confirm current row unchanged
m1p = m1.copy()
t = m1.index[cut]
grp_rows = np.where(g == g[cut])[0]
later = grp_rows[grp_rows > cut]
m1p.iloc[later, m1p.columns.get_loc('high')] += 50
m1p.iloc[later, m1p.columns.get_loc('low')] -= 50
fp = mlib.forming(m1p, 5)
print('forming row unchanged after perturbing later bars of same group:', bool(np.allclose(fp.iloc[:cut + 1].values, f.iloc[:cut + 1].values)))
mp1 = mlib.htf_on_m1(m1, mlib.resample(m1, 60), 'H1', mlib.resample(m1, 60).close.values)
mp2 = mlib.htf_on_m1(m1p, mlib.resample(m1p, 60), 'H1', mlib.resample(m1p, 60).high.values)
mp1h = mlib.htf_on_m1(m1, mlib.resample(m1, 60), 'H1', mlib.resample(m1, 60).high.values)
print('htf_on_m1(H1 high) unchanged up to perturbed row:', bool(np.allclose(mp1h.iloc[:cut + 1].values, mp2.iloc[:cut + 1].values, equal_nan=True)))

# ---- day boundaries in the real data vs END_TOD
print('max tod in data =', m1.tod.max(), 'END_TOD =', mlib.END_TOD, 'entry cutoff =', mlib.END_TOD - 15)
print('=> END_TOD force-close never triggers; entries allowed through 22:59; open positions are closed at next session open')
