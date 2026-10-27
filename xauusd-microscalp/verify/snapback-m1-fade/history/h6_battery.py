"""Independent re-run of the cost / fill / baseline battery for P1 (my simulator wrapper, same engine ea_sim._sim_next)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history')
from vlib import *
m = load_m1(); A = Arr(m); s = p1_signal(m)
def show(nm, d, t, fee=0.0):
    a = summ(d, t, None, SPLIT, fee); b = summ(d, t, SPLIT, None, fee)
    print(f'{nm:30s} TRAIN {a["per_day"]:+6.2f}/day {a["per_trade"]:+.3f}/tr | TEST {b["per_day"]:+6.2f}/day {b["trades_day"]:5.1f} tr/d '
          f'win {b["win"]:.2f} {b["per_trade"]:+.3f}/tr days>=5 {b["days_ge5"]:.2f} losing {b["losing_days"]:.2f} worst day {b["worst_day"]:+.1f} '
          f'maxDD {b["max_dd"]:+.1f} long {b["long_share"]:.2f}')
    return a, b
d, t = run(A, s); a0, b0 = show('base (bar spread + 0.05, FAIR)', d, t)
show('recorded bar spread', *run(A, s, spr=A.bar_spr))
show('flat $0.30', *run(A, s, spr=0.30))
show('base + $0.07 commission', d, t, fee=0.07)
show('OHLC fills', *run(A, s, fill='OHLC')); show('STOP fills', *run(A, s, fill='STOP'))
show('1-bar latency', *run(A, s, latency=1))
show('always long, same bars', *run(A, np.where(s != 0, 1.0, 0.0)))
show('always short, same bars', *run(A, np.where(s != 0, -1.0, 0.0)))
R = []
for z in range(50):
    dz, tz = run(A, random_like(s, z)); R.append((summ(dz, tz, None, SPLIT)['per_day'], summ(dz, tz, SPLIT, None)['per_day']))
R = np.array(R)
print(f'random directions, same bars, 50 seeds: TRAIN mean {R[:, 0].mean():+.2f} (sd {R[:, 0].std():.2f}, share >= pick {np.mean(R[:, 0] >= a0["per_day"]):.2f}); '
      f'TEST mean {R[:, 1].mean():+.2f} (sd {R[:, 1].std():.2f}, share >= pick {np.mean(R[:, 1] >= b0["per_day"]):.2f}); first 20 seeds TEST mean {R[:20, 1].mean():+.2f}, '
      f'share >= pick {np.mean(R[:20, 1] >= b0["per_day"]):.2f}')
print(f'break-even extra cost per trade: TRAIN {a0["per_trade"]:+.3f}, TEST {b0["per_trade"]:+.3f}')
