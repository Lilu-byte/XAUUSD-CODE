"""TRAIN-only refinement around the corner the first grid found (TP at the $1 cap, wide SL, long
timeout), plus daily stop/target, for the shortlisted signals. Also a 'plateau score' = mean train
per_day of the config's grid neighbours, so we pick a stable region rather than the single max."""
import warnings; warnings.filterwarnings('ignore')
import itertools, time
from multiprocessing import Pool
from sigs import *
import bracket

SHORT = ['A1_T4_ny_all', 'B1_T4_ny_rsi14', 'B2_T4_ny_below1', 'B3_T4_ny_pbge2', 'C2_NY5x_day_rsi7_lo', 'C3_NY5_day_rsi7']
TP = (0.5, 0.75, 1.0)
SL = (3, 5, 7, 10, 15, 20)
TO = (10, 15, 20, 30)
MO = (3, 10, 50)
DT = (0, 5, 10)      # day target
DL = (0, 30)         # day loss


def job(a):
    name, tp, sl, to, mo, dt, dl = a
    days, trades = bracket.H.run(bracket.SIG[name], tp, sl, timeout=to, max_open=mo, day_target=dt, day_loss=dl)
    s = summarize(days, trades, 'train')
    jul = days[days.index < pd.Timestamp('2026-08-01')].pnl.mean()
    aug = days[(days.index >= pd.Timestamp('2026-08-01')) & (days.index < SPLIT)].pnl.mean()
    return dict(name=name, tp=tp, sl=sl, to=to, mo=mo, dt=dt, dl=dl, jul=jul, aug=aug, **s)


def plateau(R):
    """mean per_day over neighbours that differ by one grid step in tp/sl/to (same name, mo, dt, dl)."""
    ax = {'tp': TP, 'sl': SL, 'to': TO}
    key = R.set_index(['name', 'tp', 'sl', 'to', 'mo', 'dt', 'dl']).per_day
    out = []
    for r in R.itertuples():
        vals = []
        for a, grid in ax.items():
            i = grid.index(getattr(r, a))
            for j in (i - 1, i + 1):
                if 0 <= j < len(grid):
                    k = dict(name=r.name, tp=r.tp, sl=r.sl, to=r.to, mo=r.mo, dt=r.dt, dl=r.dl); k[a] = grid[j]
                    vals.append(key.get(tuple(k.values()), np.nan))
        out.append(np.nanmean(vals))
    return np.array(out)


if __name__ == '__main__':
    t0 = time.time()
    grid = list(itertools.product(SHORT, TP, SL, TO, MO, DT, DL))
    with Pool(4, initializer=bracket.init) as p:
        R = pd.DataFrame(p.map(job, grid, chunksize=100))
    R['plat'] = plateau(R)
    R.to_csv('refine_train.csv', index=False)
    print('configs', len(R), 'secs', round(time.time() - t0))
    pd.set_option('display.width', 250)
    cols = ['name', 'tp', 'sl', 'to', 'mo', 'dt', 'dl', 'per_day', 'plat', 'jul', 'aug', 'trades_day', 'win', 'per_trade', 'days_ge5', 'worst_day', 'max_dd']
    for n in SHORT:
        q = R[R.name == n]
        print(f'\n== {n}: configs>0 {(q.per_day > 0).mean():.2f}; best 6 by plateau (min(jul,aug) > 0 required)')
        q = q[(q.jul > 0) & (q.aug > 0)]
        print(q.sort_values('plat', ascending=False)[cols].head(6).round(2).to_string(index=False))
