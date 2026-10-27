"""TRAIN-only: the end-of-quarter fade and first-minute-break fade with a-priori cost filters
(low recorded spread; NY-overlap session 15-19 server where spread is lowest and range highest),
wider SL / longer timeouts. Prints TRAIN halves only."""
import sys, itertools, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from sigs import *

H = Harness(); m1 = H.m1; X = build(m1)
H1 = pd.Timestamp('2026-08-01')
bar_spr = m1.spread_usd.values; hour = m1.index.hour.values
FILT = {'all': np.ones(len(m1), bool), 'spr10': bar_spr <= 0.10, 'ny': (hour >= 15) & (hour <= 19),
        'ny_spr10': (bar_spr <= 0.10) & (hour >= 15) & (hour <= 19)}
SIGS = {}
for thr in (0.6, 0.8, 1.0):
    s = strong_close_fade(X, 'f15', thr, 0.9, (14, 15))
    for fn, f in FILT.items(): SIGS[f'scf{thr}_{fn}'] = np.where(f, s, 0)
for thr in (0.0, 0.1):
    s = first_minute_break_fade(X, 'f15', (1,), 'close', thr)
    for fn, f in FILT.items(): SIGS[f'fmb{thr}_{fn}'] = np.where(f, s, 0)
GRID = list(itertools.product((0.5, 0.7, 1.0), (1.0, 2.0, 3.0, 5.0), (3, 5, 10, 20), (1, 3)))
rows = []; t0 = time.time()
for name, s in SIGS.items():
    for tp, sl, to, mo in GRID:
        days, trades = H.run(s, tp, sl, timeout=to, max_open=mo)
        d = days[days.index < SPLIT]; t = trades[trades.entry < SPLIT]
        rows.append(dict(sig=name, tp=tp, sl=sl, to=to, mo=mo, per_day=d.pnl.mean(), h0=d[d.index < H1].pnl.mean(),
                         h1=d[d.index >= H1].pnl.mean(), trades_day=len(t) / len(d), per_trade=t.pnl.mean(),
                         win=(t.pnl > 0).mean(), worst=d.pnl.min()))
R = pd.DataFrame(rows); R['minh'] = R[['h0', 'h1']].min(axis=1)
R.to_csv(FC + 'bracket2_train.csv', index=False)
print(f'{len(SIGS)} signals x {len(GRID)} = {len(R)} configs, {time.time() - t0:.0f}s')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
g = R.groupby('sig').agg(mean_pt=('per_trade', 'mean'), frac_pos=('per_trade', lambda v: (v > 0).mean()),
                         frac_both=('minh', lambda v: (v > 0).mean()), best_minh=('minh', 'max'), tr_day=('trades_day', 'mean'))
print('\nPer signal, over the whole bracket grid (robustness view):')
print(g.sort_values('mean_pt', ascending=False).round(3).to_string())
print('\nTop 20 configs by min half per_day:')
print(R.sort_values('minh', ascending=False).head(20).round(3).to_string(index=False))
