"""Stage 3 (TRAIN only): TP/SL/timeout/max_open grid for each candidate, FAIR fills, base spread.
Prints per candidate the best TRAIN configs that are positive in BOTH train halves."""
import itertools, time
from sigs import *
H = Harness(); m = H.m1
C = candidates(m)
MID = pd.Timestamp('2026-08-01')
TPS = (0.1, 0.2, 0.3, 0.5, 0.75, 1.0); SLS = (0.5, 1, 2, 3, 5, 8); TOS = (1, 2, 3, 5, 10, 20, 30); MOS = (1, 3, 10, 50)
rows = []; t0 = time.time()
for name, sig in C.items():
    for tp, sl, to, mo in itertools.product(TPS, SLS, TOS, MOS):
        days, tr = H.run(sig, tp, sl, timeout=to, max_open=mo)
        d = days[days.index < SPLIT]; t = tr[tr.entry < SPLIT]
        rows.append(dict(sig=name, tp=tp, sl=sl, to=to, mo=mo, per_day=d.pnl.mean(), A=d.pnl[d.index < MID].mean(),
                         B=d.pnl[d.index >= MID].mean(), trades_day=len(t) / len(d), per_trade=t.pnl.mean(), win=(t.pnl > 0).mean()))
df = pd.DataFrame(rows); df.to_csv('bracket_train.csv', index=False)
print('runs', len(df), 'secs', round(time.time() - t0))
pd.set_option('display.width', 250)
for name in C:
    q = df[df.sig == name]
    rb = q[(q.A > 0) & (q.B > 0)]
    print(f'\n== {name}: configs {len(q)}, positive both halves {len(rb)}, share positive train {(q.per_day > 0).mean():.2f}; median per_day {q.per_day.median():.2f}')
    print(q.sort_values('per_day', ascending=False).head(4).round(3).to_string(index=False))
    if len(rb): print(' robust best:'); print(rb.assign(mn=np.minimum(rb.A, rb.B)).sort_values('mn', ascending=False).head(4).round(3).to_string(index=False))
