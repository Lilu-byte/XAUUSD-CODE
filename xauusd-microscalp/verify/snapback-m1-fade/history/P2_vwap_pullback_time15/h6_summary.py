"""Summary numbers for the verdict: cost/fill battery (own code), 100-seed random baseline, always long/short,
TEST significance, and how many demo days would be needed to tell +$3/day from zero."""
import sys, json; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *
m = load_tf('M1'); A = Arr(m); s = A.signal()
d, t = A.run(s); out = {}
for nm, kw, fee in (('base', {}, 0), ('bar spread', dict(spr='bar'), 0), ('flat $0.30', dict(spr='wide'), 0), ('base + $0.07 commission', {}, 0.07),
                    ('OHLC fills', dict(fill='OHLC'), 0), ('STOP fills', dict(fill='STOP'), 0), ('1-bar latency', dict(latency=1), 0)):
    dd, tt = (d, t) if not kw else A.run(s, **kw)
    tr, te = summ(dd, tt, None, SPLIT, fee), summ(dd, tt, SPLIT, None, fee)
    out[nm] = dict(train=tr['per_day'], test=te['per_day']); print(f'{nm:26s} TRAIN {tr["per_day"]:+6.2f}/day  TEST {te["per_day"]:+6.2f}/day ({te["per_trade"]:+.3f}/tr)')
R = np.array([[summ(*A.run(random_like(s, z)), a, b)['per_day'] for a, b in ((None, SPLIT), (SPLIT, None))] for z in range(100)])
te = summ(d, t, SPLIT, None); tr = summ(d, t, None, SPLIT)
print(f'random directions, same bars, 100 seeds: TRAIN {R[:, 0].mean():+.2f} (share >= pick {(R[:, 0] >= tr["per_day"]).mean():.2f}); '
      f'TEST {R[:, 1].mean():+.2f} (sd {R[:, 1].std():.2f}; share >= pick {(R[:, 1] >= te["per_day"]).mean():.2f})')
for nm, sg in (('always long', np.where(s != 0, 1.0, 0.0)), ('always short', np.where(s != 0, -1.0, 0.0))):
    dd, tt = A.run(sg); print(f'{nm}: TRAIN {summ(dd, tt, None, SPLIT)["per_day"]:+.2f}  TEST {summ(dd, tt, SPLIT, None)["per_day"]:+.2f}')
p = d[d.index >= SPLIT].pnl
se = p.std(ddof=1) / np.sqrt(len(p))
print(f'TEST days {len(p)}: mean {p.mean():+.2f}, sd {p.std(ddof=1):.1f}, t {p.mean() / se:.2f}; days needed for t = 2 at this mean and sd: {(2 * p.std(ddof=1) / p.mean()) ** 2:.0f}')
print(f'TEST long share {te["long_share"]:.2f}; TRAIN long share {tr["long_share"]:.2f}; TEST days >= +$5 {te["days_ge5"]:.2f}, losing days {te["losing_days"]:.2f}')
json.dump(dict(battery=out, rand_test=float(R[:, 1].mean()), rand_test_share=float((R[:, 1] >= te['per_day']).mean())), open(OUT + 'h6_summary.json', 'w'), indent=1)
