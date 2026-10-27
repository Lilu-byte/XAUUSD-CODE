"""TRAIN-only bracket grid on the candidate signals chosen from edge_scan (signals zeroed on TEST
rows so nothing about TEST is computed). FAIR fills, base spread. Writes bracket_train.csv."""
import warnings; warnings.filterwarnings('ignore')
import itertools, time, sys
from multiprocessing import Pool
from sigs import *

CANDS = {
    'A1_T4_ny_all': ('T4', 'all', 'ny', 'any'),
    'A2_T5_ny_all': ('T5', 'all', 'ny', 'any'),
    'A3_NY5_ny_all': ('NY5', 'all', 'ny', 'any'),
    'A4_T4_lonny_all': ('T4', 'all', 'lonny', 'any'),
    'B1_T4_ny_rsi14': ('T4', 'rsi14_40', 'ny', 'any'),
    'B2_T4_ny_below1': ('T4', 'below1', 'ny', 'any'),
    'B3_T4_ny_pbge2': ('T4', 'pbge2', 'ny', 'any'),
    'C1_NY5x_day_rsi7': ('NY5x', 'rsi7_30', 'day', 'any'),
    'C2_NY5x_day_rsi7_lo': ('NY5x', 'rsi7_30', 'day', 'lo'),
    'C3_NY5_day_rsi7': ('NY5', 'rsi7_30', 'day', 'any'),
}
TP = (0.1, 0.2, 0.3, 0.5, 0.75, 1.0)
SL = (0.5, 1, 2, 3, 5, 10)
TO = (3, 5, 10, 20, 30)
MO = (1, 3, 10, 50)
CD = (0, 2)
TRAIN = None


def init():
    global H, SIG, TRAIN
    H = Harness()
    TRAIN = H.m1.index < SPLIT
    SIG = {k: np.where(TRAIN, make(*v), 0) for k, v in CANDS.items()}


def job(args):
    name, tp, sl, to, mo, cd = args
    days, trades = H.run(SIG[name], tp, sl, timeout=to, max_open=mo, cooldown=cd)
    s = summarize(days, trades, 'train')
    jul = days[days.index < pd.Timestamp('2026-08-01')].pnl.mean()
    aug = days[(days.index >= pd.Timestamp('2026-08-01')) & (days.index < SPLIT)].pnl.mean()
    return dict(name=name, tp=tp, sl=sl, to=to, mo=mo, cd=cd, jul=jul, aug=aug, **s)


if __name__ == '__main__':
    t0 = time.time()
    grid = list(itertools.product(CANDS, TP, SL, TO, MO, CD))
    with Pool(4, initializer=init) as p:
        rows = p.map(job, grid, chunksize=200)
    B = pd.DataFrame(rows)
    B.to_csv('bracket_train.csv', index=False)
    print('configs', len(B), 'secs', round(time.time() - t0))
    pd.set_option('display.width', 250)
    cols = ['name', 'tp', 'sl', 'to', 'mo', 'cd', 'per_day', 'jul', 'aug', 'trades_day', 'win', 'per_trade', 'days_ge5', 'worst_day', 'max_dd']
    for n in CANDS:
        q = B[B.name == n]
        print(f'\n== {n}: best 5 by train per_day; share of configs > 0: {(q.per_day > 0).mean():.2f}; median {q.per_day.median():.2f}')
        print(q.sort_values('per_day', ascending=False)[cols].head(5).round(3).to_string(index=False))
