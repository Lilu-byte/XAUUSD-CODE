"""Common window May 2025 - Oct 2026: the pick alone and added to the GoldAllAgree + GoldAsiaBreak pair.
Daily P&L by exit date; trading days = unique dates of the M5 data. Also max simultaneous open lots."""
from common import *
P = '/mnt/project-files/'
m5 = load('M5'); days = pd.DatetimeIndex(np.unique(m5.index.normalize()))
aa = pd.read_csv(P + 'xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
ab = pd.read_csv(P + 'xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
dp = lambda t, col: t.groupby(t.exit_time.dt.normalize())[col].sum().reindex(days, fill_value=0.0)
pair = dp(aa, 'pnl_usd') + dp(ab, 'pnl')
d = load('H1'); a = atr(d, 14); sig = np.where(d1_regime(d, 200), dc_sig(d, 120), 0.0)
VERS = {'pick (pyramid +2ATR)': dict(sl=2 * a, trail_m=4.0, add_trig=2.0, max_units=2), 'no pyramid': dict(sl=2 * a, trail_m=4.0)}
def st(p):
    eq = p.cumsum(); mo = p.groupby(p.index.to_period('M')).sum()
    return dict(per_day=round(p.mean(), 2), max_dd=round((eq - eq.cummax()).min(), 0), losing_months=f'{(mo < 0).sum()}/{len(mo)}',
                worst_month=round(mo.min(), 0), total=round(p.sum(), 0))
print('pair alone          ', st(pair))
iv = [(r.entry_time, r.exit_time, 1) for r in aa.itertuples()] + [(r.entry_time, r.exit_time, 1) for r in ab.itertuples()]
def max_lots(intervals):
    ev = sorted([(s, 1) for s, e, _ in intervals] + [(e, -1) for s, e, _ in intervals], key=lambda x: (x[0], x[1]))
    cur = mx = 0; tot = {}; last = None
    for tm, k in ev:
        if last is not None and cur >= 3: tot[cur] = tot.get(cur, pd.Timedelta(0)) + (tm - last)
        cur += k; mx = max(mx, cur); last = tm
    return mx, {k: round(v.total_seconds() / 3600, 0) for k, v in tot.items()}
print('pair max open lots, hours at >=3 lots:', max_lots(iv))
for name, kw in VERS.items():
    t = tx.tsim(d, sig, a, **kw); t = t[t.entry_time >= days[0]]
    mine = dp(t, 'pnl')
    print(f'\n== {name}: trades {int((t.unit == 1).sum())}, units {len(t)}')
    print('  alone             ', st(mine))
    print('  pair + this       ', st(pair + mine))
    print('  corr with pair (daily)', round(np.corrcoef(pair, mine)[0, 1], 2),
          '| weekly', round(np.corrcoef(pair.resample('W').sum(), mine.resample('W').sum())[0, 1], 2))
    ivm = iv + [(r.entry_time, r.exit_time + pd.Timedelta(minutes=59), 1) for r in t.itertuples()]
    print('  max open lots pair+this, hours spent at >=3 lots:', max_lots(ivm))
    mo = pd.DataFrame({'pair': pair, 'this': mine}).groupby(pair.index.to_period('M')).sum().round(0)
    mo['sum'] = mo.pair + mo.this; print('  monthly:', mo.T.to_string())
    if name.startswith('pick'): mo.to_csv('common_monthly_pick.csv')
