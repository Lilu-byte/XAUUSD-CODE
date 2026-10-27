"""Stage 1 grid: entries x exit designs, scored on the TRAIN window only (2016-07-29 .. 2021-12-31).
Prints train $/day, train years, drawdown, trades/yr, time in market. No test numbers are computed here."""
from common import *
import itertools, json

d1 = load('H1'); d4 = load('H4')
rows = []


def run(tf, d, ename, sig, xkind, xp, regime):
    s = sig.copy()
    if regime: s = np.where((s == 1) & d1_regime(d), 1, np.where(s == -1, -1, 0)).astype(float) if (s == 1).any() else s
    if regime and (s == -1).any():   # shorts only when D1 below its SMA200
        reg = d1_regime(d); s = np.where((s == -1) & ~reg, -1, np.where(s == 1, 1, 0)).astype(float)
    kw = exits(d, xkind, xp)
    t = tx.tsim(d, s, atr(d, 14), **kw)
    r = tx.summary(t, d, *TRAIN, label=f'{tf} {ename} | {xkind}{xp if xp else ""} | {"D1>SMA200" if regime else "-"}')
    tt = t[t.entry_time < pd.Timestamp(TRAIN[1])]
    yr = tx.by_year(tt, d[d.index < pd.Timestamp(TRAIN[1])])
    r.update({str(y): v for y, v in yr.items()})
    r['in_mkt%'] = round(100 * (tt.xi - tt.ei).sum() / (d.index < pd.Timestamp(TRAIN[1])).sum(), 0)
    r['avg_hold_h'] = round(((tt.exit_time - tt.entry_time).dt.total_seconds() / 3600).mean(), 0)
    r['best_trade'] = round(tt.pnl.max(), 0)
    rows.append(r)


ENTRIES = {
    'H1': [('maxi L', lambda d: maxi_sig(d)), ('maxi LS', lambda d: maxi_sig(d, long_only=False)),
           ('dc20 L', lambda d: dc_sig(d, 20)), ('dc55 L', lambda d: dc_sig(d, 55)), ('dc120 L', lambda d: dc_sig(d, 120)),
           ('ema20/80x L', lambda d: ema_cross_sig(d, 20, 80)), ('ema50/200x L', lambda d: ema_cross_sig(d, 50, 200))],
    'H4': [('dc20 L', lambda d: dc_sig(d, 20)), ('dc55 L', lambda d: dc_sig(d, 55)),
           ('ema10/40x L', lambda d: ema_cross_sig(d, 10, 40)), ('ema20/80x L', lambda d: ema_cross_sig(d, 20, 80))],
}
EXITS = [('fixed', 0), ('chand', 3), ('chand', 4.5), ('chand', 6), ('chan', 20), ('chan', 60), ('chan', 120),
         ('ma', 50), ('ma', 100), ('ma', 200)]
for tf, d in (('H1', d1), ('H4', d4)):
    for (en, fn), (xk, xp), reg in itertools.product(ENTRIES[tf], EXITS, (False, True)):
        run(tf, d, en, fn(d), xk, xp, reg)
res = pd.DataFrame(rows)
res.to_csv('grid_train.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400)
cols = ['label', 'per_day', 'trades', 'tr_yr', 'win', 'pf', 'max_dd', 'in_mkt%', 'avg_hold_h', 'best_trade'] + [str(y) for y in range(2016, 2022)]
print('variants:', len(res))
print(res.sort_values('per_day', ascending=False)[cols].head(45).to_string(index=False))
print('\nby exit kind (median train $/day):'); res['x'] = res.label.str.split('|').str[1].str.strip()
print(res.groupby('x').per_day.median().sort_values())
