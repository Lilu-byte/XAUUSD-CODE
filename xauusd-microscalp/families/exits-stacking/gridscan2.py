"""Stage D (TRAIN only, mlib v2 conventions): averaging-down grid baskets (gridsim2, FAIR 4-vertex in-bar path,
base spread, force-close at the session's last bar / 22:58).
direction signal x step x max levels x basket target x basket stop x time limit. Writes gridscan2_train.csv."""
from sigs2 import *
from gridsim2 import *
from multiprocessing import Pool
import itertools, time

SIGS = ['AB', 'AS', 'CF', 'COL', 'HTF', 'PB', 'MR']
STEP = [0.5, 1.0, 2.0, 3.0, 5.0]
LEV = [3, 5, 10, 20, 50]
BTP = [0.1, 0.3, 0.5, 1.0]
BSL = [0.0, 20.0, 50.0, 100.0]
TMAX = [0, 30]
G = {}


def init():
    m1, H = train_harness(); S = build(m1); tr = m1.index < SPLIT
    G['H'] = H; G['S'] = {k: S[k][tr] for k in SIGS}


def job(a):
    s, step, lev, btp, bsl, tm = a
    H = G['H']
    days, bask, eqm, levm = run_grid(H, G['S'][s], step, lev, btp, bsl, tmax=tm)
    r = gsumm(H, days, bask, eqm, levm, 'train')
    r.update(sig=s, step=step, maxlev=lev, btp=btp, bsl=bsl, tmax=tm,
             pd_jul=days.pnl[days.index < HALF].mean(), pd_aug=days.pnl[(days.index >= HALF) & (days.index < SPLIT)].mean())
    return r


if __name__ == '__main__':
    t0 = time.time()
    jobs = list(itertools.product(SIGS, STEP, LEV, BTP, BSL, TMAX))
    with Pool(4, initializer=init) as p:
        rows = p.map(job, jobs, chunksize=20)
    R = pd.DataFrame(rows)
    R.to_csv(OUT + 'gridscan2_train.csv', index=False)
    print('configs', len(R), 'secs %.0f' % (time.time() - t0))
    pd.set_option('display.width', 260)
    c = ['sig', 'step', 'maxlev', 'btp', 'bsl', 'tmax', 'per_day', 'positions_day', 'per_position', 'basket_win', 'days_ge5',
         'worst_day', 'worst_intraday', 'max_dd_float', 'max_levels', 'stopout_1to100', 'stopout_1to500', 'pd_jul', 'pd_aug']
    print('positive TRAIN per_day:', (R.per_day > 0).sum(), ' both halves > 0:', ((R.pd_jul > 0) & (R.pd_aug > 0)).sum(),
          ' per_day >= 5:', (R.per_day >= 5).sum(), ' no stop-out at 1:100:', (~R.stopout_1to100).sum())
    print('\ntop 15 by per_day:'); print(R.sort_values('per_day', ascending=False)[c].head(15).round(2).to_string(index=False))
    q = R[(R.pd_jul > 0) & (R.pd_aug > 0)]
    print('\ntop 15 by per_day with both inner halves > 0:'); print(q.sort_values('per_day', ascending=False)[c].head(15).round(2).to_string(index=False))
    print('\nper signal: median per_position, best per_day, share of configs with per_day > 0, median worst_day')
    print(R.groupby('sig').agg(pp_med=('per_position', 'median'), pd_best=('per_day', 'max'), pos_share=('per_day', lambda x: (x > 0).mean()),
                               worst_med=('worst_day', 'median'), basket_win_med=('basket_win', 'median')).round(3))
    print('\nby max levels (median): '); print(R.groupby('maxlev')[['per_position', 'per_day', 'basket_win', 'worst_day', 'max_dd_float']].median().round(3))
    print('\nby basket stop (median): '); print(R.groupby('bsl')[['per_position', 'per_day', 'basket_win', 'worst_day', 'max_dd_float']].median().round(3))
