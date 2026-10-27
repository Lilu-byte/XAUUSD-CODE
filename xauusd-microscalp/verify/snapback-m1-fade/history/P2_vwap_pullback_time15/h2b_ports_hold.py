"""(1b) Hold-time sensitivity of the ports. On M1 (h3_neighbours.out) longer holds than the family's grid edge (15 bars)
look even better on TRAIN and TEST (30-60 minutes). Does a longer hold rescue the port on the data before the M1 file?
Same port as h2_ports.py (M5 k 1.05 / 1.35, M15 k 1.30 / 0.59), holds 15/30/45/60 minutes, flat $0.20 per trade,
20 random-direction seeds per cell. Nothing is selected from this table."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *
PER = {'M5': [('2025-05..2025-12', '2025-05-05', '2026-01-01'), ('2026-01..06-25', '2026-01-01', '2026-06-26'), ('M1 period', '2026-06-26', '2026-10-10')],
       'M15': [('2022-07..2023-12', '2022-07-01', '2024-01-01'), ('2024', '2024-01-01', '2025-01-01'), ('2025', '2025-01-01', '2026-01-01'),
               ('2026-01..06-25', '2026-01-01', '2026-06-26'), ('M1 period', '2026-06-26', '2026-10-10')]}
CFG = {'M5': (48, [1.05, 1.35], {15: 3, 30: 6, 45: 9, 60: 12}), 'M15': (16, [1.30, 0.59], {15: 1, 30: 2, 45: 3, 60: 4})}
rows = []
for tf in ('M5', 'M15'):
    m = load_tf(tf); A = Arr(m, tf); natr, ks, holds = CFG[tf]
    for k in ks:
        s = A.signal(k=k, L=1, atr_n=natr)
        for hm, hb in holds.items():
            d, t = A.run(s, sl=25.0, hold=hb, mo=3, spr=0.20); dg, tg = A.run(s, sl=25.0, hold=hb, mo=3, spr=0.0)
            R = [A.run(random_like(s, z), sl=25.0, hold=hb, mo=3, spr=0.20) for z in range(20)]
            cells = []
            for nm, a, b in PER[tf]:
                a, b = pd.Timestamp(a), pd.Timestamp(b)
                r = summ(d, t, a, b); g = summ(dg, tg, a, b); rr = np.array([summ(*x, a, b)['per_day'] for x in R])
                rows.append(dict(tf=tf, k=k, hold_min=hm, period=nm, per_day=r['per_day'], per_trade=r['per_trade'], gross_per_trade=g['per_trade'],
                                 trades_day=r['trades_day'], worst_day=r['worst_day'], max_dd=r['max_dd'], rand=rr.mean(), share_rand_ge=(rr >= r['per_day']).mean()))
                cells.append(f'{nm} {r["per_day"]:+6.2f} [{g["per_trade"]:+.2f}] rnd {rr.mean():+.2f}')
            print(f'{tf} k {k:.2f} hold {hm:2d}m: ' + ' | '.join(cells))
pd.DataFrame(rows).to_csv(OUT + 'h2b_ports_hold.csv', index=False)
X = pd.DataFrame(rows); pre = X[X.period != 'M1 period']
print(f'\ncells before the M1 file: {len(pre)}; $/day > 0 in {(pre.per_day > 0).sum()}; gross $/trade > 0 in {(pre.gross_per_trade > 0).sum()}; '
      f'beats >= 90% of random seeds in {(pre.share_rand_ge <= 0.10).sum()}; median $/day {pre.per_day.median():+.2f}')
m1p = X[X.period == 'M1 period']
print(f'cells on the M1 period: {len(m1p)}; $/day > 0 in {(m1p.per_day > 0).sum()}; median $/day {m1p.per_day.median():+.2f}')
print('configurations simulated (incl. 20 random seeds per cell):', 2 * 2 * 4 * 22)
