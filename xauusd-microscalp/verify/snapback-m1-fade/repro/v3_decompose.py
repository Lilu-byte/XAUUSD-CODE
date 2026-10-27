"""Where does the P&L come from? Per-trade bid moves in the trade direction: gap close[i]->open[i+1] (not earned),
bar i+1 (open->close), bar i+2, bar i+3; split by direction and period; plus hour-of-day median spread stress."""
from common import *

R = Rep(); m = R.m; H = R.H
raw = raw_signal(m.close.values); s0 = entry_filter(m, raw)
days, T = R.run(s0)
o, c = H.o, H.c
ei = T.ei.values; d = T.dir.values
ok = ei + 3 < len(c)
gap = (o[ei + 1] - c[ei]) * d
b1 = (c[ei + 1] - o[ei + 1]) * d
b2 = (c[ei + 2] - c[ei + 1]) * d
b3 = (c[ei + 3] - c[ei + 2]) * d
X = pd.DataFrame({'per': np.where(T.entry >= SPLIT, 'test', 'train'), 'dir': np.where(d == 1, 'long', 'short'),
                  'gap': gap, 'b1': b1, 'b2': b2, 'b3': b3, 'pnl': T.pnl.values,
                  'stop': T.pnl.values <= -SL + 1e-6})
print('mean $ per trade (bid moves in trade direction; pnl after base spread and $10 stop):')
print(X.groupby(['per', 'dir'])[['gap', 'b1', 'b2', 'b3', 'pnl']].mean().round(3).to_string())
print(X.groupby(['per'])[['gap', 'b1', 'b2', 'b3', 'pnl']].mean().round(3).to_string())
print('median per trade:'); print(X.groupby(['per'])[['b1', 'b2', 'b3', 'pnl']].median().round(3).to_string())
print('stop share', X.groupby('per').stop.mean().round(3).to_dict())
# P&L excluding the largest-|pnl| trades: how much of the edge is in tails?
for per in ('train', 'test'):
    p = X.pnl[X.per == per].sort_values(ascending=False).values
    print(f'{per}: trades {len(p)} total {p.sum():+.1f}; best 10 trades {p[:10].sum():+.1f}; best 20 {p[:20].sum():+.1f}; '
          f'without best 2% of trades {p[int(len(p) * 0.02):].sum():+.1f}; trades with pnl>+3: {(p > 3).sum()} sum {p[p > 3].sum():+.1f}')

# spread stress: bar MINIMUM spread is LOWER on these busy bars than elsewhere. Charge the hour-of-day median
# recorded spread of ALL bars (the typical quote at that hour) + $0.05 instead, or the max of the two.
sp = m.spread_usd
hmed = sp.groupby(m.index.hour).transform('median').values
H._spr['hourmed'] = hmed + 0.05
H._spr['max_bar_hourmed'] = np.maximum(sp.values, hmed) + 0.05
for model in ('hourmed', 'max_bar_hourmed'):
    dd, TT = R.run(s0, spread=model)
    for per in ('train', 'test'):
        print(fmt(f'spread={model} {per}', stats(dd, TT, per)))
print('hour-median spread $ on the trades entry bars: mean %.3f vs base model on the same bars %.3f'
      % (hmed[ei + 1].mean() + 0.05, R.spr('base')[ei + 1].mean()))
