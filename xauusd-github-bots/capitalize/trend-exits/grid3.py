"""Stage 3 (TRAIN only): pyramiding / breakeven / regime-length checks on the stage-2 pick
(H1 close > prior 120-bar high, long only, D1 close > SMA200, initial stop 2 ATR(14), chandelier 4 ATR(14))."""
from common import *
d = load('H1'); a = atr(d, 14)
rows = []
def go(label, s, **kw):
    t = tx.tsim(d, s, a, **kw)
    r = tx.summary(t, d, *TRAIN, label=label)
    tt = t[t.entry_time < pd.Timestamp(TRAIN[1])]; dtr = d[d.index < pd.Timestamp(TRAIN[1])]
    r.update({str(y): v for y, v in tx.by_year(tt, dtr).items()})
    eq = tx.mtm_daily(tt, d); eq = eq[eq.index < pd.Timestamp(TRAIN[1])]; r['mtm_dd'] = round((eq - eq.cummax()).min(), 0)
    r['adds'] = int((tt.unit == 2).sum()); rows.append(r); return t
base = dict(sl=2 * a, trail_m=4.0)
s200 = np.where(d1_regime(d, 200), dc_sig(d, 120), 0.0)
go('pick (no pyramid)', s200, **base)
for at in (1.0, 2.0, 3.0):
    go(f'pyramid add at +{at} ATR, stop->BE', s200, **base, add_trig=at, max_units=2)
for bt in (1.0, 2.0):
    go(f'breakeven at +{bt} ATR, no add', s200, **base, be_trig=bt)
go('regime D1 SMA100', np.where(d1_regime(d, 100), dc_sig(d, 120), 0.0), **base)
go('regime D1 SMA300', np.where(d1_regime(d, 300), dc_sig(d, 120), 0.0), **base)
go('no regime', dc_sig(d, 120), **base)
res = pd.DataFrame(rows)
pd.set_option('display.width', 250)
cols = ['label', 'per_day', 'trades', 'adds', 'win', 'pf', 'max_dd', 'mtm_dd'] + [str(y) for y in range(2016, 2022)]
print(res[cols].to_string(index=False)); res.to_csv('grid3_train.csv', index=False)
