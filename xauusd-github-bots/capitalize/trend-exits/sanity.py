"""Sanity checks on the pick's trade list: fills, stops, look-ahead, pyramid mechanics, swap."""
from common import *
d = load('H1'); a = atr(d, 14); reg = d1_regime(d, 200); sig = np.where(reg, dc_sig(d, 120), 0.0)
t = tx.tsim(d, sig, a, sl=2 * a, trail_m=4.0, add_trig=2.0, max_units=2)
O, H, L, C = (d[x].values for x in ('open', 'high', 'low', 'close'))
u1 = t[t.unit == 1]; u2 = t[t.unit == 2]
ei = u1.ei.astype(int).values
print('1. every unit-1 entry follows a signal bar:', bool((sig[ei - 1] == 1).all()))
print('   entry = next open + 0.30 + 0.10:', bool(np.allclose(u1.entry.values, O[ei] + 0.4)))
hh = d.high.shift().rolling(120).max().values
print('   signal close > prior-120 high (excludes signal bar):', bool((C[ei - 1] > hh[ei - 1]).all()))
# regime: D1 value used at H1 bar must be from a D1 bar that closed before it
D = load('D1'); ok = (D.close > sma(D.close, 200))
k = np.searchsorted(D.index.values, d.index.values, side='right') - 2   # previous completed D1 bar
manual = np.where(k >= 0, ok.values[np.clip(k, 0, None)], False)
print('2. D1 regime equals "previous completed D1 bar" lookup on', round(100 * (manual == reg).mean(), 2), '% of H1 bars')
# 3. exits: never better than the bar allows, stops filled at level - slip or worse
xi = t.xi.astype(int).values
print('3. exit price within [low - slip, high] of the exit bar:', bool(((t.exit.values >= L[xi] - 0.1 - 1e-9) & (t.exit.values <= H[xi] + 1e-9)).all()))
print('   exit reasons:', t.why.value_counts().to_dict())
# 4. pyramid: unit 2 shares exit with a unit 1, enters after unit-1 entry, trigger close >= e1 + 2 ATR(signal)
m = u2.merge(u1, on='xi', suffixes=('_2', '_1'))
print('4. adds:', len(u2), '| matched to a unit-1 exit:', len(m), '| add after entry1:', bool((m.ei_2 > m.ei_1).all()))
trig_ok = [(C[int(r.ei_2) - 1] >= r.entry_1 + 2 * a.values[int(r.ei_1) - 1] - 1e-9) for r in m.itertuples()]
print('   add bar trigger condition true:', all(trig_ok), '| add exits at or above entry1 - slip - gap:',
      round((m.exit_2 >= m.entry_1 - 0.1 - 1e-9).mean() * 100, 1), '%')
# 5. no overlap between consecutive positions
s1 = u1.sort_values('ei'); print('5. positions never overlap:', bool((s1.ei.values[1:] >= s1.xi.values[:-1]).all()))
# 6. swap: nights x 0.126
print('6. swap/unit avg', round(t.swap.mean(), 2), '| total swap', round(t.swap.sum(), 0), '| gross', round(t.gross.sum(), 0))
print('   hold hours: median', round(((u1.exit_time - u1.entry_time).dt.total_seconds() / 3600).median(), 0),
      'max', round(((u1.exit_time - u1.entry_time).dt.total_seconds() / 3600).max(), 0))
print('7. biggest winners:'); print(t.sort_values('pnl').tail(5)[['entry_time', 'exit_time', 'unit', 'entry', 'exit', 'pnl', 'why']].to_string(index=False))
print('   biggest losers:'); print(t.sort_values('pnl').head(5)[['entry_time', 'exit_time', 'unit', 'entry', 'exit', 'pnl', 'why']].to_string(index=False))
# 8. share of profit from top trades
tp = t.sort_values('pnl', ascending=False); print('8. top 10 trades = ', round(tp.pnl.head(10).sum(), 0), 'of total', round(t.pnl.sum(), 0))
