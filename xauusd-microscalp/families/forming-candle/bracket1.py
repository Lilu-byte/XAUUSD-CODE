"""TRAIN-only bracket grid for the forming-M15 strong-close fade and first-minute break fade.
Prints only TRAIN summaries (plus first/second half of TRAIN)."""
import sys, time, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/forming-candle')
from sigs import *

H = Harness(); m1 = H.m1; X = build(m1)
H1 = pd.Timestamp('2026-08-01')


def tr_sum(days, trades):
    d = days[days.index < SPLIT]; t = trades[trades.entry < SPLIT]
    s = summarize(d, t)
    a = d[d.index < H1].pnl.mean(); b = d[d.index >= H1].pnl.mean()
    return dict(per_day=s['per_day'], h0=a, h1=b, trades_day=s['trades_day'], win=s['win'], per_trade=s['per_trade'],
                worst=s['worst_day'], dd=s['max_dd'])


SIGS = {}
for thr, cl, mins in itertools.product((0.4, 0.6, 0.8, 1.0), (0.75, 0.9), ((14,), (15,), (14, 15), (13, 14, 15))):
    SIGS[f'scf_t{thr}_c{cl}_m{"".join(map(str, mins))}'] = strong_close_fade(X, 'f15', thr, cl, mins)
for mins, mode, thr in itertools.product(((1,), (1, 2)), ('close', 'touch'), (0.0, 0.1, 0.25)):
    SIGS[f'fmb_{mode}_t{thr}_m{"".join(map(str, mins))}'] = first_minute_break_fade(X, 'f15', mins, mode, thr)

GRID = list(itertools.product((0.3, 0.5, 0.7, 1.0), (0.5, 1.0, 2.0, 3.0), (2, 3, 5, 10), (1, 3)))
t0 = time.time()
rows = []
for name, sg in SIGS.items():
    for tp, sl, to, mo in GRID:
        days, trades = H.run(sg, tp, sl, timeout=to, max_open=mo)
        r = dict(sig=name, tp=tp, sl=sl, to=to, mo=mo); r.update(tr_sum(days, trades)); rows.append(r)
R = pd.DataFrame(rows)
R.to_csv(FC + 'bracket1_train.csv', index=False)
print(f'{len(SIGS)} signals x {len(GRID)} brackets = {len(R)} configs in {time.time() - t0:.0f}s')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
R['minh'] = R[['h0', 'h1']].min(axis=1)
print('\nBest bracket per signal (by min of the two TRAIN halves):')
b = R.loc[R.groupby('sig').minh.idxmax()].sort_values('minh', ascending=False)
print(b.round(3).to_string(index=False))
print('\nSignal-level average per_trade over the whole bracket grid (robustness):')
print(R.groupby('sig')[['per_trade', 'per_day', 'trades_day']].mean().sort_values('per_trade', ascending=False).round(3).to_string())
