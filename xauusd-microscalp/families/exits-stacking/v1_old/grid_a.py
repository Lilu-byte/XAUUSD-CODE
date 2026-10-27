"""Stage A (TRAIN only): signal x TP x SL x timeout, max_open=1, FAIR fills, base spread.
Writes grid_a_train.csv; prints the best rows and the 'per_trade + spread paid' residual check."""
from sigs import *
import os
REP = os.environ.get('REPAIR', '1') == '1'   # repaired early-July spreads (default)
SUF = '_rep' if REP else '_orig'
from multiprocessing import Pool
import itertools, time

TPS = [0.10, 0.20, 0.30, 0.50, 0.75, 1.00]
SLS = [0.10, 0.20, 0.30, 0.50, 0.75, 1.00, 2.0, 3.0, 5.0, 10.0, 20.0]
TOS = [1, 2, 3, 5, 10, 20, 30]
G = {}


def init():
    m1 = repaired_m1() if REP else load_m1(); S = build(m1); tr = m1.index < SPLIT
    G['H'] = Harness(m1[tr]); G['S'] = {k: v[tr] for k, v in S.items()}


def job(a):
    sname, tp, sl, to = a
    H = G['H']
    d, t = run_pw(H, G['S'][sname], tp, sl, timeout=to)
    r = summ(d, t, 'train')
    r.update(sig=sname, tp=tp, sl=sl, timeout=to, avg_bars=t.bars.mean(), avg_spr_in=t.spr.mean(),
             tp_frac=(t.kind == 0).mean(), sl_frac=(t.kind == 1).mean(), mixed_frac=(t.kind == 2).mean())
    return r


if __name__ == '__main__':
    t0 = time.time()
    sigsn = ['AB', 'CF', 'COL', 'FADE', 'HTF', 'PB', 'HCOL']
    jobs = list(itertools.product(sigsn, TPS, SLS, TOS))
    with Pool(4, initializer=init) as p:
        rows = p.map(job, jobs, chunksize=20)
    R = pd.DataFrame(rows)
    R.to_csv(OUT + f'grid_a_train{SUF}.csv', index=False)
    print('configs', len(R), 'secs %.0f' % (time.time() - t0))
    pd.set_option('display.width', 250)
    c = ['sig', 'tp', 'sl', 'timeout', 'per_day', 'trades_day', 'win', 'pwin', 'per_trade', 'avg_spr_in', 'avg_bars',
         'days_ge5', 'worst_day', 'pd_jul', 'pd_aug']
    print('positive TRAIN per_day:', (R.per_day > 0).sum(), ' positive per_trade:', (R.per_trade > 0).sum())
    print(R.sort_values('per_trade', ascending=False)[c].head(25).round(3).to_string(index=False))
    print('\nbest per signal by per_trade:')
    print(R.loc[R.groupby('sig').per_trade.idxmax()][c].round(3).to_string(index=False))
