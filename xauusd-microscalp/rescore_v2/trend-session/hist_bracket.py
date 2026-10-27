"""Coarse sanity check on OLDER data (M5 bars 2025-05-05..2026-06-25, before the M1 file; not TEST):
run the harness on M5 bars (each 'bar' = 5 minutes, FAIR fills, recorded M5 spread + $0.05) for the
NY-session trend idea. Coarse bars hide intrabar drift on ambiguous bars, so this is rough."""
import warnings; warnings.filterwarnings('ignore')
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *
from hist_check import m5, t_m5, t15, t1, t4, rsi

END = pd.Timestamp('2026-06-26')
d = m5.copy()
d['spread_usd'] = d.spread * 0.01
d['tod'] = d.index.hour * 60 + d.index.minute
agree = t_m5 + t15 + t1 + t4
dirn = np.where(agree == 4, 1, np.where(agree == -4, -1, 0))
sel = (d.index < END)
d = d[sel]; dirn = dirn[sel]
H = Harness(d)
tod = d.tod.values
ny = (tod >= 930) & (tod < 1080)
e20 = ema(d.close, 20).values
below = np.where(dirn > 0, d.close.values < e20, d.close.values > e20)
r14 = rsi(d.close, 14).values
dip = np.where(dirn > 0, r14 < 45, r14 > 55)
rng = (d.high - d.low)
print('M5 bars', len(d), 'days', len(H.dates), 'median M5 range by half-year:')
print(rng.groupby(pd.Grouper(freq='6MS')).median().round(2).to_string())
sigs = {'T4 ny all': np.where(ny, dirn, 0), 'T4 ny belowEMA20(M5)': np.where(ny & below, dirn, 0),
        'T4 ny rsi14<45(M5)': np.where(ny & dip, dirn, 0), 'T4 all-day all': np.where((tod >= 540) & (tod < 1320), dirn, 0)}
for name, s in sigs.items():
    for tp, sl, to in ((1.0, 10, 4), (1.0, 10, 6), (0.5, 5, 2), (1.0, 5, 2)):
        days, tr = H.run(s, tp, sl, timeout=to, max_open=50)
        r = summarize(days, tr)
        h1 = days[days.index < pd.Timestamp('2025-12-01')].pnl.mean(); h2 = days[days.index >= pd.Timestamp('2025-12-01')].pnl.mean()
        rl = np.mean([summarize(*H.run(random_like(s, k), tp, sl, timeout=to, max_open=50))['per_day'] for k in range(5)])
        print(f'{name:24s} tp{tp} sl{sl} to{to*5}m: per_day {r["per_day"]:6.2f} (2025H2 {h1:6.2f}, 2026H1 {h2:6.2f}) '
              f'trades/day {r["trades_day"]:5.1f} per_trade {r["per_trade"]:6.3f} win {r["win"]:.2f} random {rl:6.2f}')

# second pass: the corner the M1-train grid preferred (TP $1, SL $20, 30 minutes)
print('\n-- corner configs (TP 1, SL 20, timeout 6 M5 bars = 30 min, max_open 10) --')
for name, s in sigs.items():
    days, tr = H.run(s, 1.0, 20, timeout=6, max_open=10)
    r = summarize(days, tr)
    yr = days.pnl.groupby(pd.Grouper(freq='QS')).mean().round(2).to_dict()
    rl = np.mean([summarize(*H.run(random_like(s, k), 1.0, 20, timeout=6, max_open=10))['per_day'] for k in range(5)])
    print(f'{name:24s} per_day {r["per_day"]:6.2f} per_trade {r["per_trade"]:6.3f} win {r["win"]:.3f} trades/day {r["trades_day"]:.1f} random {rl:6.2f} by quarter', {k.strftime("%Y-%m"): v for k, v in yr.items()})

# Nyao-score dip analogue on M5 history: score>=5 (no D1 filter), M5 RSI7<30 (long) / >70 (short),
# 09:00-21:59, recorded spread below its median
from features import nyao_scores
nb, ns = nyao_scores(m5)
nb, ns = nb[sel], ns[sel]
nyd = np.where((nb >= 5) & ~(ns >= 5), 1, np.where((ns >= 5) & ~(nb >= 5), -1, 0))
r7 = rsi(d.close, 7).values
lo = d.spread_usd.values < np.median(d.spread_usd.values)
dayw = (tod >= 540) & (tod < 1320)
s = np.where(dayw & lo & np.where(nyd > 0, r7 < 30, r7 > 70), nyd, 0)
print('\n-- Nyao dip analogue (M5 RSI7) --')
for tp, sl, to in ((1.0, 20, 6), (1.0, 10, 4)):
    days, tr = H.run(s, tp, sl, timeout=to, max_open=10)
    r = summarize(days, tr)
    yr = days.pnl.groupby(pd.Grouper(freq='QS')).mean().round(2).to_dict()
    rl = np.mean([summarize(*H.run(random_like(s, k), tp, sl, timeout=to, max_open=10))['per_day'] for k in range(5)])
    print(f'tp{tp} sl{sl} to{to*5}m per_day {r["per_day"]:6.2f} per_trade {r["per_trade"]:6.3f} win {r["win"]:.3f} trades/day {r["trades_day"]:.1f} random {rl:6.2f}', {k.strftime("%Y-%m"): v for k, v in yr.items()})
