"""TRAIN-only bracket grid for the candidate signals (FAIR fills, base spread)."""
import sys, time, itertools; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from sigs import *
t0 = time.time()
H = Harness(); m = H.m1; f = build(m); C = candidates(m, f)
TP = (0.1, 0.2, 0.3, 0.5, 0.7, 1.0); SL = (0.5, 1, 2, 3, 5, 8); TO = (3, 5, 10, 20, 30); MO = (1, 3, 10)
rows = []
trmask = H.dates < SPLIT; Amask = H.dates < A_SPLIT
for name, sig in C.items():
    for tp, sl, to, mo in itertools.product(TP, SL, TO, MO):
        days, trades = H.run(sig, tp, sl, to, mo)
        s = summarize(days, trades, 'train')
        dA = days.pnl[Amask].mean(); dB = days.pnl[trmask & ~Amask].mean()
        rows.append(dict(sig=name, tp=tp, sl=sl, to=to, mo=mo, perA=dA, perB=dB, **s))
r = pd.DataFrame(rows); r.to_csv('bracket1_train.csv.gz', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
cols = ['sig', 'tp', 'sl', 'to', 'mo', 'per_day', 'perA', 'perB', 'trades_day', 'win', 'per_trade', 'worst_day', 'max_dd']
print('configs', len(r), 'time', round(time.time() - t0))
for name in C:
    s = r[r.sig == name].sort_values('per_day', ascending=False)
    print(s[cols].head(5).round(3).to_string(index=False))
    print(f'   frac configs >0: {(s.per_day > 0).mean():.2f}   median per_day {s.per_day.median():.2f}')
