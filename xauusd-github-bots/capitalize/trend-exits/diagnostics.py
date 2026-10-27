"""POST-HOC diagnostics (run after the single test scoring; nothing here changed the pick):
does the trailing exit beat the Maxi-style fixed target out of sample on the same entry, and how does the
original Maxi0-912 rule look in this simulator (no same-bar re-entry after an intrabar stop)."""
from common import *
d = load('H1'); a = atr(d, 14); reg = d1_regime(d, 200); sig = np.where(reg, dc_sig(d, 120), 0.0)
W = {'train': TRAIN, 'test': TEST, 'common': COMMON}
def show(nm, t):
    print(f'{nm:52s}', {w: tx.summary(t, d, *v)['per_day'] for w, v in W.items()}, '| test dd', tx.summary(t, d, *TEST)['max_dd'])
show('pick entry + fixed SL2/TP4 ATR (Maxi exit)', tx.tsim(d, sig, a, sl=2 * a, tp=4 * a))
show('pick entry + chandelier 4 ATR (final, no pyramid)', tx.tsim(d, sig, a, sl=2 * a, trail_m=4.0))
show('pick entry + chandelier 4 ATR + pyramid', tx.tsim(d, sig, a, sl=2 * a, trail_m=4.0, add_trig=2.0, max_units=2))
show('Maxi0-912 original (L+S, fixed) in tx', tx.tsim(d, maxi_sig(d, long_only=False), a, sl=2 * a, tp=4 * a))
show('Maxi0-912 long only + chandelier 4 ATR', tx.tsim(d, maxi_sig(d), a, sl=2 * a, trail_m=4.0))
# daily Sharpe-like ratio on the common window: pair vs pair + final
m5 = load('M5'); days = pd.DatetimeIndex(np.unique(m5.index.normalize())); P = '/mnt/project-files/'
aa = pd.read_csv(P + 'xauusd-mt5/expected_trades_M5.csv', parse_dates=['exit_time']); ab = pd.read_csv(P + 'xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['exit_time'])
dp = lambda t, col: t.groupby(t.exit_time.dt.normalize())[col].sum().reindex(days, fill_value=0.0)
pair = dp(aa, 'pnl_usd') + dp(ab, 'pnl')
t = tx.tsim(d, sig, a, sl=2 * a, trail_m=4.0); t = t[t.entry_time >= days[0]]; mine = dp(t, 'pnl')
sr = lambda p: round(p.mean() / p.std() * np.sqrt(252), 2)
print('annualised daily Sharpe, common window: pair', sr(pair), '| final alone', sr(mine), '| pair + final', sr(pair + mine),
      '| pair x1.39 (same $/day by scaling)', sr(pair * 1.39))
