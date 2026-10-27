"""TRAIN-only: every library signal, follow and fade, through 4 reference brackets in the harness (FAIR/base,
max_open 1). Finds anything whose CAPPED (TP<=$1) result is positive."""
import sys, time; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from library import *
t0 = time.time()
H = Harness(); m = H.m1; f = build(m); L = library(m, f)
REF = [(0.2, 1, 2), (0.5, 2, 5), (1.0, 3, 5), (1.0, 8, 10)]
Am = H.dates < A_SPLIT; Tm = H.dates < SPLIT
rows = []
for name, d in L.items():
    for dn, sgn in (('follow', 1), ('fade', -1)):
        r = dict(sig=name, dir=dn)
        for tp, sl, to in REF:
            days, trades = H.run(sgn * d, tp, sl, to, 1)
            s = summarize(days, trades, 'train')
            r[f'pd{tp}_{sl}'] = s['per_day']; r[f'pt{tp}_{sl}'] = s['per_trade']; r[f'n{tp}_{sl}'] = s['trades_day']
            r[f'A{tp}_{sl}'] = days.pnl[Am].mean(); r[f'B{tp}_{sl}'] = days.pnl[Tm & ~Am].mean()
        rows.append(r)
t = pd.DataFrame(rows); t.to_csv('scan5_train.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
print('signals x dirs', len(t), ' runs', len(t) * len(REF), ' time', round(time.time() - t0))
for tp, sl, to in REF:
    k = f'{tp}_{sl}'
    s = t.sort_values(f'pd{k}', ascending=False)
    print(f'\n== bracket TP {tp} SL {sl} TO {to}: n positive {(t[f"pd{k}"] > 0).sum()}, positive both halves {((t[f"A{k}"] > 0) & (t[f"B{k}"] > 0)).sum()}')
    print(s[['sig', 'dir', f'pd{k}', f'pt{k}', f'n{k}', f'A{k}', f'B{k}']].head(12).round(3).to_string(index=False))
