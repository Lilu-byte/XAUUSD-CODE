"""Stage B (TRAIN only): management layer on top of Stage A brackets.
signal x base bracket (top-2 per signal from Stage A by per_trade + 5 'user-style' brackets)
x spread gate (none, <=0.05/0.10/0.15/0.20 on the entry bar, <=0.10/0.15 on the previous bar)
x max_open (1,3,5,10,50) x cooldown (0,2,3,5).  Writes grid_b_train.csv."""
from sigs import *
import os
REP = os.environ.get('REPAIR', '1') == '1'   # repaired early-July spreads (default)
SUF = '_rep' if REP else '_orig'
from multiprocessing import Pool
import itertools, time

USER = [(0.10, 1.0, 5), (0.30, 0.30, 3), (0.50, 2.0, 10), (1.00, 0.50, 10), (0.20, 20.0, 30)]
GATES = [(None, 0), (0.05, 0), (0.10, 0), (0.15, 0), (0.20, 0), (0.10, 1), (0.15, 1)]
MO = [1, 3, 5, 10, 50]
CD = [0, 2, 3, 5]
G = {}


def init():
    m1 = repaired_m1() if REP else load_m1(); S = build(m1); tr = m1.index < SPLIT
    G['H'] = Harness(m1[tr]); G['S'] = {}
    for k, v in S.items():
        for g, lag in GATES:
            G['S'][(k, g, lag)] = (v if g is None else gate(v, m1, g, lag))[tr]


def job(a):
    sname, (tp, sl, to), (g, lag), mo, cd = a
    d, t = run_pw(G['H'], G['S'][(sname, g, lag)], tp, sl, timeout=to, max_open=mo, cooldown=cd)
    r = summ(d, t, 'train')
    r.update(sig=sname, tp=tp, sl=sl, timeout=to, gate=g if g else 0, lag=lag, max_open=mo, cooldown=cd,
             avg_spr_in=t.spr.mean() if len(t) else np.nan)
    return r


if __name__ == '__main__':
    t0 = time.time()
    A = pd.read_csv(OUT + f'grid_a_train{SUF}.csv')
    jobs = []
    for s, gA in A.groupby('sig'):
        top = gA.sort_values('per_trade', ascending=False).head(2)
        bases = [(r.tp, r.sl, int(r.timeout)) for r in top.itertuples()] + USER
        bases = list(dict.fromkeys(bases))
        jobs += list(itertools.product([s], bases, GATES, MO, CD))
    with Pool(4, initializer=init) as p:
        rows = p.map(job, jobs, chunksize=20)
    R = pd.DataFrame(rows)
    R.to_csv(OUT + f'grid_b_train{SUF}.csv', index=False)
    print('configs', len(R), 'secs %.0f' % (time.time() - t0))
    pd.set_option('display.width', 250)
    c = ['sig', 'tp', 'sl', 'timeout', 'gate', 'lag', 'max_open', 'cooldown', 'per_day', 'trades_day', 'pwin', 'per_trade',
         'avg_spr_in', 'days_ge5', 'worst_day', 'max_dd', 'pd_jul', 'pd_aug']
    print('positive TRAIN per_day:', (R.per_day > 0).sum(), ' positive per_trade:', (R.per_trade > 0).sum())
    print(R.sort_values('per_trade', ascending=False)[c].head(20).round(3).to_string(index=False))
    q = R[R.trades_day >= 20]
    print('\nbest per_day with >=20 trades/day:')
    print(q.sort_values('per_day', ascending=False)[c].head(15).round(3).to_string(index=False))
    print('\nmedian per_trade by gate/lag:'); print(R.groupby(['gate', 'lag']).per_trade.median().round(3))
    print('\nmedian per_trade by max_open:'); print(R.groupby('max_open').per_trade.median().round(3))
    print('median per_day by max_open:'); print(R.groupby('max_open').per_day.median().round(2))
    print('\nmedian per_trade by cooldown:'); print(R.groupby('cooldown').per_trade.median().round(3))
