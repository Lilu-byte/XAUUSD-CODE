"""TRAIN-only refinement of the first-minute-break fade (new M15/M5 candle's first M1 closes beyond the
previous candle's high/low -> fade), cost filters, and the union with the quarter-end strong-close fade."""
import sys, itertools, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from sigs import *

H = Harness(); m1 = H.m1; X = build(m1)
H1 = pd.Timestamp('2026-08-01')
bs = m1.spread_usd.values; hour = m1.index.hour.values
FILT = {'spr10': bs <= 0.10, 'spr12': bs <= 0.12, 'ny': (hour >= 15) & (hour <= 19), 'all': np.ones(len(m1), bool)}
SIGS = {}
for p in ('f15', 'f5'):
    for thr in (0.05, 0.1, 0.2):
        s = first_minute_break_fade(X, p, (1,), 'close', thr)
        for fn, f in FILT.items(): SIGS[f'fmb_{p}_{thr}_{fn}'] = np.where(f, s, 0)
u = strong_close_fade(X, 'f15', 0.8, 0.9, (14, 15)); v = first_minute_break_fade(X, 'f15', (1,), 'close', 0.1)
uni = np.where(u != 0, u, v)
for fn in ('spr10', 'ny'): SIGS[f'union_{fn}'] = np.where(FILT[fn], uni, 0)
GRID = list(itertools.product((0.3, 0.5, 0.7), (2.0, 3.0), (3, 5, 10), (1, 3)))
rows = []; t0 = time.time()
for name, s in SIGS.items():
    for tp, sl, to, mo in GRID:
        days, trades = H.run(s, tp, sl, timeout=to, max_open=mo)
        d = days[days.index < SPLIT]; t = trades[trades.entry < SPLIT]
        rows.append(dict(sig=name, tp=tp, sl=sl, to=to, mo=mo, per_day=d.pnl.mean(), h0=d[d.index < H1].pnl.mean(),
                         h1=d[d.index >= H1].pnl.mean(), trades_day=len(t) / len(d), per_trade=t.pnl.mean(), win=(t.pnl > 0).mean()))
R = pd.DataFrame(rows); R['minh'] = R[['h0', 'h1']].min(axis=1)
R.to_csv(FC + 'bracket3_train.csv', index=False)
print(f'{len(SIGS)} signals x {len(GRID)} = {len(R)} configs, {time.time() - t0:.0f}s')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
g = R.groupby('sig').agg(mean_pt=('per_trade', 'mean'), mean_pd=('per_day', 'mean'), frac_both=('minh', lambda v: (v > 0).mean()),
                         best_minh=('minh', 'max'), tr_day=('trades_day', 'mean'))
print(g.sort_values('mean_pt', ascending=False).round(3).to_string())
