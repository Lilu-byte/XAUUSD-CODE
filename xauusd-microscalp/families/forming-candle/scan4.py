"""TRAIN only. For every scan1 condition and both directions (continuation / fade):
(a) capped edge: mean of clip(signed move, -1.2, +1.2) at 1-3 min (what a <= $1 bracket can harvest),
(b) a small bracket grid through the harness (FAIR/base, max_open 1).
Shows whether any forming-candle condition survives the TP <= $1 cap."""
import sys, itertools, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from scan1 import conds, X, F, TR, HALF, ND_TR, m1
from feats import *

H = Harness(m1)
H1 = pd.Timestamp('2026-08-01')
C = {}
C.update(conds(X, 'f5', (1, 2, 3, 4, 5)))
C.update(conds(X, 'f15', (1, 3, 5, 8, 11, 14, 15)))
GRID = list(itertools.product((0.5, 1.0), (1.0, 3.0), (3, 10)))
t0 = time.time(); rows = []
for name, (msk, d) in C.items():
    if (msk & TR).sum() < 150: continue
    for sgn, lab in ((1, 'cont'), (-1, 'fade')):
        s = np.where(msk, d * sgn, 0)
        mt = msk & TR
        r = dict(name=name, dir=lab, sig_day=mt.sum() / ND_TR, spread=X.spr.values[mt].mean())
        for k in (1, 2, 3):
            v = F[k][mt] * d[mt] * sgn
            r[f'raw{k}'] = np.nanmean(v); r[f'cap{k}'] = np.nanmean(np.clip(v, -1.2, 1.2))
        best = -9
        for tp, sl, to in GRID:
            days, trades = H.run(s, tp, sl, timeout=to, max_open=1)
            t = trades[trades.entry < SPLIT]; dd = days[days.index < SPLIT]
            pt = t.pnl.mean()
            if pt > best:
                best = pt; r.update(tp=tp, sl=sl, to=to, per_trade=pt, per_day=dd.pnl.mean(),
                                    h0=dd[dd.index < H1].pnl.mean(), h1=dd[dd.index >= H1].pnl.mean(), win=(t.pnl > 0).mean())
        rows.append(r)
R = pd.DataFrame(rows)
R.to_csv(FC + 'scan4_train.csv', index=False)
print(f'{len(R)} condition-directions x {len(GRID)} brackets in {time.time() - t0:.0f}s')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
print('\ncorrelation of capped edge minus spread vs best bracket per_trade:',
      np.corrcoef(R.cap2 - R.spread, R.per_trade)[0, 1].round(3))
print('\nTop 30 by best bracket per_trade (TRAIN, chosen over 8 brackets -> optimistic):')
print(R.sort_values('per_trade', ascending=False).head(30).round(3).to_string(index=False))
print('\nShare of condition-directions with best per_trade > 0:', (R.per_trade > 0).mean().round(3))
