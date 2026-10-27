"""Disclosure check (6 extra configurations): the three picks with a take-profit of $1.00 and $0.50 instead of the
pure time exit, same N / stop / max_open, base spread, FAIR fills. Plus a hand check of 3 trades of pick C."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-history')
from hlib import *
PICKS = [('A', 'M15', 2, 4.0, 1, 4, 25, 3, '2022-07-01', '2025-01-01'), ('B', 'M5', 1, 4.0, 0, 6, 10, 1, '2025-05-05', '2026-01-01'),
         ('C', 'M15', 2, 4.0, 1, 2, 25, 3, '2022-07-01', '2025-01-01')]
cache = {}
for nm, tf, n, k, g, N, sl, mo, lo, hi in PICKS:
    if tf not in cache:
        d = load_tf(tf); f = features(d, tf); cache[tf] = (d, f, Scorer(d, tf, f.ar))
    d, f, S = cache[tf]; s = signal(d, f, n, k, g)
    for tp in (1.0, 0.5):
        for fill in ('FAIR', 'OHLC'):
            days, T = S.run(s, N, sl, mo, tp=tp, fill=fill)
            a = stats(days, T, lo, hi); b = stats(days, T, hi, None)
            print(f"{nm} TP {tp} {fill}: SEL {a['per_day']:+.2f}/d {a['per_trade']:+.3f}/tr win {a['win']:.2f} | TEST {b['per_day']:+.2f}/d {b['per_trade']:+.3f}/tr win {b['win']:.2f}")
    if nm == 'C':
        days, T = S.run(s, N, sl, mo)
        o = d.open.values; c = d.close.values; sp = d.spread_usd.values + 0.05
        for j in (5, 50, 150):
            t = T.iloc[j]; i = d.index.get_loc(t.entry); x = i + t.bars
            if t.dir == 1: man = c[x] - (o[i + 1] + sp[i + 1])
            else: man = o[i + 1] - (c[x] + sp[x])
            print(f"  hand check trade {j}: signal {t.entry} dir {t.dir:+d} bars {t.bars} sim {t.pnl:+.2f} manual {man:+.2f}")
