"""(2) random-direction baseline (50 seeds) and always-long/short on the same bars; (3) costs, fills, latency, entry
spread cap, exit-at-next-open and stop slippage. All on the fixed P2 rule; nothing is selected here."""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/repro/P2_vwap_pullback_time15')
from p2lib import *
R = Rep(); m = R.m
raw, *_ = signal_df(m)
s = entry_filter(m, raw)
res = {}; nconf = 0
def rec(name, d, T, fee=0.0):
    global nconf; nconf += 1
    res[name] = {per: stats(d, T, per, fee) for per in ('train', 'test')}
    print(fmt(name + ' TRAIN', res[name]['train'])); print(fmt(name + ' TEST', res[name]['test']))
d, T = R.run(s); rec('base (FAIR, bar+0.05)', d, T)
base = res['base (FAIR, bar+0.05)']
for per in ('train', 'test'):
    print(f'  {per}: breakeven extra cost per trade = {base[per]["per_trade"]:+.3f}; day t-stat {base[per]["t_stat"]:+.2f}; '
          f'day sd {base[per]["day_sd"]:.1f}; long trades ${base[per]["long_pnl"]:+.0f} ({base[per]["n_long"]}), '
          f'short trades ${base[per]["short_pnl"]:+.0f} ({base[per]["n_short"]})')
rec('recorded bar spread', *R.run(s, spread='bar'))
rec('base + $0.07 commission', d, T, fee=0.07)
rec('flat $0.30', *R.run(s, spread='flat0.30'))
rec('flat $0.40', *R.run(s, spread='flat0.40'))
rec('fill OHLC', *R.run(s, fill='OHLC'))
rec('fill STOP', *R.run(s, fill='STOP'))
rec('latency 1 bar', *R.run(entry_filter(m, raw, lat=1)))
rec('latency 2 bars', *R.run(entry_filter(m, raw, lat=2)))
rec('entry only if spread < $0.30', *R.run(entry_filter(m, raw, max_spread=0.30, strict_lt=True)))
rec('exit at next bar open (pysim)', *pysim_frame(R, s, exit_next_open=True))
rec('stop slippage $1 (pysim)', *pysim_frame(R, s, stop_slip=1.0))
dw, Tw = R.run(entry_filter(m, raw, lat=1), spread='flat0.30')
rec('flat 0.30 + 0.07 comm + latency 1', dw, Tw, fee=0.07)
# baselines on the same signal bars
rnd = {'train': [], 'test': []}
for z in range(50):
    dz, Tz = R.run(entry_filter(m, random_like(raw, z)))
    for per in rnd: rnd[per].append(stats(dz, Tz, per)['per_day'])
for per in ('train', 'test'):
    x = np.array(rnd[per]); pk = base[per]['per_day']
    res[f'random_{per}'] = dict(mean=x.mean(), sd=x.std(), best=x.max(), worst=x.min(), share_ge_pick=float((x >= pk).mean()),
                                z_pick=(pk - x.mean()) / x.std())
    print(f'random directions, 50 seeds, {per.upper()}: mean {x.mean():+.2f} sd {x.std():.2f} best {x.max():+.2f} '
          f'share of seeds >= pick {(x >= pk).mean():.2f}  (pick {pk:+.2f}, z {(pk - x.mean()) / x.std():+.2f})')
rec('always long, same bars', *R.run(entry_filter(m, np.where(raw != 0, 1.0, 0.0))))
rec('always short, same bars', *R.run(entry_filter(m, np.where(raw != 0, -1.0, 0.0))))
print('simulator configurations scored in this script (excluding 50 random seeds):', nconf)
json.dump(res, open(OUT + 'v2_battery.json', 'w'), indent=1, default=float)
