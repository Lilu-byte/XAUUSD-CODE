"""Stage A (TRAIN only, mlib v2): signal x TP x SL x timeout, max_open=1, FAIR fills, base spread.
Writes stageA2_train.csv; prints summaries. resid = per_trade + spread paid (0 for a martingale with no edge)."""
from sigs2 import *
from multiprocessing import Pool
import itertools, time

TPS = [0.10, 0.20, 0.30, 0.50, 0.75, 1.00]
SLS = [0.30, 0.50, 0.75, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0]
TOS = [1, 2, 3, 5, 10, 20, 30]
SIGS = ['AB', 'AS', 'CF', 'COL', 'HTF', 'PB', 'MR', 'MR6']
G = {}


def init():
    m1, H = train_harness(); S = build(m1); tr = m1.index < SPLIT
    G['H'] = H; G['S'] = {k: v[tr] for k, v in S.items()}


def job(a):
    sname, tp, sl, to = a
    d, t = run_pw(G['H'], G['S'][sname], tp, sl, timeout=to)
    r = summ(d, t, 'train')
    r.update(sig=sname, tp=tp, sl=sl, timeout=to, avg_bars=t.bars.mean(), avg_spr=t.spr.mean(),
             tp_frac=(t.kind == 0).mean(), sl_frac=(t.kind == 1).mean(), mixed_frac=(t.kind == 2).mean(),
             to_frac=(t.kind == 3).mean())
    r['resid'] = r['per_trade'] + r['avg_spr']
    return r


if __name__ == '__main__':
    t0 = time.time()
    jobs = list(itertools.product(SIGS, TPS, SLS, TOS))
    with Pool(4, initializer=init) as p:
        rows = p.map(job, jobs, chunksize=20)
    R = pd.DataFrame(rows)
    R.to_csv(OUT + 'stageA2_train.csv', index=False)
    print('configs', len(R), 'secs %.0f' % (time.time() - t0))
    pd.set_option('display.width', 250)
    c = ['sig', 'tp', 'sl', 'timeout', 'per_day', 'trades_day', 'pwin', 'per_trade', 'avg_spr', 'resid', 'avg_bars',
         'worst_day', 'pd_jul', 'pd_aug']
    print('positive TRAIN per_day:', (R.per_day > 0).sum(), ' positive in BOTH inner halves:', ((R.pd_jul > 0) & (R.pd_aug > 0)).sum())
    print('\nper signal: best per_trade config, median resid, share positive per_day')
    for s, g in R.groupby('sig'):
        b = g.loc[g.per_trade.idxmax()]
        print(f'  {s:4s} best {b.tp:.2f}/{b.sl:5.2f}/{int(b.timeout):2d}: per_day {b.per_day:+7.2f} trades/day {b.trades_day:6.1f} '
              f'per_trade {b.per_trade:+.3f} pwin {b.pwin:.2f} jul {b.pd_jul:+.2f} aug {b.pd_aug:+.2f} | median resid {g.resid.median():+.3f} '
              f'| pos per_day {(g.per_day > 0).mean():.2f}')
    print('\ntop 20 by per_day with jul>0 and aug>0:')
    q = R[(R.pd_jul > 0) & (R.pd_aug > 0)]
    print(q.sort_values('per_day', ascending=False)[c].head(20).round(3).to_string(index=False))
    print('\nCF (coin flip): resid by TP (rows) x SL (cols), timeout 30')
    x = R[(R.sig == 'CF') & (R.timeout == 30)].pivot(index='tp', columns='sl', values='resid')
    print(x.round(3).to_string())
    print('\nCF: pwin by TP x SL, timeout 30')
    print(R[(R.sig == 'CF') & (R.timeout == 30)].pivot(index='tp', columns='sl', values='pwin').round(2).to_string())
