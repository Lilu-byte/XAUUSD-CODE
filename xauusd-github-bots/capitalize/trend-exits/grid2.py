"""Stage 2 (TRAIN only): refine the family that won stage 1 on 2016-07..2021-12:
H1 close above the prior N-bar high, long only, only while the last closed D1 close is above its SMA200,
initial stop k*ATR(14), trailing exit. Then pyramiding on the pick."""
from common import *
import itertools
d = load('H1'); a = atr(d, 14); reg = d1_regime(d)
rows = []
def go(label, s, **kw):
    t = tx.tsim(d, s, a, **kw)
    r = tx.summary(t, d, *TRAIN, label=label)
    tt = t[t.entry_time < pd.Timestamp(TRAIN[1])]; dtr = d[d.index < pd.Timestamp(TRAIN[1])]
    r.update({str(y): v for y, v in tx.by_year(tt, dtr).items()})
    eq = tx.mtm_daily(tt, d); eq = eq[eq.index < pd.Timestamp(TRAIN[1])]; r["mtm_dd"] = round((eq - eq.cummax()).min(), 0)
    rows.append(r); return t
for N, (xk, xp), k in itertools.product((55, 80, 120, 160), (('chand', 3), ('chand', 4), ('chan', 20), ('chan', 30)), (2, 3)):
    s = np.where(reg, dc_sig(d, N), 0.0)
    kw = exits(d, xk, xp); kw['sl'] = k * a
    go(f'N{N} {xk}{xp} k{k}', s, **kw)
res = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400)
cols = ['label', 'per_day', 'trades', 'win', 'pf', 'max_dd', 'mtm_dd', 'pos_months'] + [str(y) for y in range(2016, 2022)]
print(res[cols].to_string(index=False))
# neighbour smoothing over N for each exit/k
res['N'] = res.label.str.extract(r'N(\d+)').astype(int); res['xk'] = res.label.str.split(' ', n=1).str[1]
piv = res.pivot(index='xk', columns='N', values='per_day'); print('\n$/day train by N (rows exit+k):'); print(piv)
sm = piv.T.rolling(3, center=True, min_periods=2).mean().T; print('\nneighbour-averaged over N:'); print(sm.round(3))
res.to_csv('grid2_train.csv', index=False)
