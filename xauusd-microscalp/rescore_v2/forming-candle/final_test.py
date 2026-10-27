"""The ONE look at TEST for the 3 picks chosen on TRAIN (bracket2/bracket3). Prints everything the
report needs: TRAIN/TEST FAIR-base, TEST OHLC-base, FAIR-bar, FAIR-wide, random-direction baseline
(20 seeds, same bars), TEST edge() table."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/rescore_v2/forming-candle')
from sigs import *

H = Harness(); m1 = H.m1; X = build(m1)
bs = m1.spread_usd.values; hr = m1.index.hour.values
ny = (hr >= 15) & (hr <= 19)
fmb = first_minute_break_fade(X, 'f15', (1,), 'close', 0.1)
PICKS = {
    'fmb15_ny': (np.where(ny, fmb, 0), 0.5, 2.0, 5, 1),
    'fmb15_spr10': (np.where(bs <= 0.10, fmb, 0), 0.5, 3.0, 5, 1),
    'scf15_ny': (np.where(ny, strong_close_fade(X, 'f15', 0.8, 0.9, (14, 15)), 0), 1.0, 3.0, 3, 3),
}
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
for name, (s, tp, sl, to, mo) in PICKS.items():
    print(f'\n===== {name}: tp={tp} sl={sl} timeout={to} max_open={mo}')
    days, trades = H.run(s, tp, sl, timeout=to, max_open=mo)
    tr = summarize(days, trades, 'train'); te = summarize(days, trades, 'test')
    print('TRAIN FAIR/base', {k: round(v, 3) for k, v in tr.items()})
    print('TEST  FAIR/base', {k: round(v, 3) for k, v in te.items()})
    tt = trades[trades.entry >= SPLIT]
    print('TEST avg bars held', round(tt.bars.mean(), 2), ' exit mix: pnl>0', round((tt.pnl > 0).mean(), 3))
    for fill, spr in (('OHLC', 'base'), ('FAIR', 'bar'), ('FAIR', 'wide')):
        d2, t2 = H.run(s, tp, sl, timeout=to, max_open=mo, fill=fill, spread=spr)
        print(f'TEST  {fill}/{spr}', {k: round(v, 3) for k, v in summarize(d2, t2, 'test').items() if k in ('per_day', 'trades_day', 'win', 'per_trade')})
    rnd = []
    for seed in range(20):
        d3, t3 = H.run(random_like(s, seed), tp, sl, timeout=to, max_open=mo)
        rnd.append(summarize(d3, t3, 'test')['per_day'])
    print('TEST random-direction same bars per_day (20 seeds): mean', round(np.mean(rnd), 3), 'sd', round(np.std(rnd), 3))
    print(edge(m1, s).round(3).to_string())
