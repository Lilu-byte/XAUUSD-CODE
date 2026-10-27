"""Stage 2b (TRAIN only): refine the two regions stage 2a found, with TP $2-6 instead of a pure time exit,
break-even and trailing variants, stops $5-25 and caps 1-5.
  R1 'snap'  : no VWAP gate, 3-bar move, short holds (N 2-4)            -- the round-1 snap-back
  R2 'toward': VWAP-'toward' gate (move runs toward VWAP from the other side; the fade trades back to the VWAP side),
               long holds (N 8-15)"""
import sys, itertools, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from sb import *
from multiprocessing import Pool

BE = [(0.0, 0.0, 0.0), (1.0, 0.2, 0.0), (2.0, 0.2, 0.0), (0.0, 0.0, 1.5), (0.0, 0.0, 3.0)]
JOBS = []
for mode, ths in (('atr', [3.0, 3.25, 3.5, 3.75, 4.0]), ('usd', [6, 7, 8, 9])):
    for th, fresh, sg in itertools.product(ths, (False, True), (0.0, 0.15)):
        JOBS.append(('snap', (3, mode, th, 'none', fresh, sg),
                     list(itertools.product((2, 3, 4), (5.0, 8.0, 10.0, 15.0), (1000.0, 2.0, 3.0, 4.0, 6.0), (1, 2, 3), BE))))
for k, (mode, ths) in itertools.product((2, 3), (('atr', [2.0, 2.5, 3.0, 3.5]), ('usd', [3, 4, 5, 6]))):
    for th, fresh, sg in itertools.product(ths, (False, True), (0.0, 0.15)):
        JOBS.append(('toward', (k, mode, th, 'toward', fresh, sg),
                     list(itertools.product((8, 10, 12, 15), (10.0, 25.0), (1000.0, 3.0, 6.0), (1, 3, 5),
                                            [BE[0], BE[2], BE[4]]))))
G = {}


def init():
    m, H = load_train(); G['m'] = m; G['H'] = H; G['f'] = feats(m)


def job(j):
    reg, sd, ex = j
    s = fade_signal(G['f'], *sd)
    out = []
    for N, sl, tp, mo, (bt, bl, tr) in ex:
        d, t = G['H'].run_x(s, (tp,), sl, N, mo, 0, bt, bl, tr)
        r = halves(d, t)
        r.update(region=reg, k=sd[0], mode=sd[1], th=sd[2], gate=sd[3], fresh=sd[4], sgate=sd[5], N=N, sl=sl, tp=tp, mo=mo,
                 be_trig=bt, be_lock=bl, trail=tr)
        out.append(r)
    return out


if __name__ == '__main__':
    t0 = time.time()
    with Pool(4, initializer=init) as p:
        rows = sum(p.map(job, JOBS, chunksize=1), [])
    R = pd.DataFrame(rows)
    R.to_csv(FAM + 's2b_refine_train.csv.gz', index=False)
    R['minh'] = R[['pd_A', 'pd_B']].min(axis=1); R['both'] = R.minh > 0
    print('configs', len(R), 'secs %.0f' % (time.time() - t0))
    pd.set_option('display.width', 250)
    c = ['k', 'mode', 'th', 'fresh', 'sgate', 'N', 'sl', 'tp', 'mo', 'be_trig', 'trail', 'pd_tr', 'pd_A', 'pd_B', 'tpd_tr', 'pt_tr',
         'win_tr', 'wd_tr', 'dd_tr', 'wt_tr', 'ls_tr']
    for reg in ('snap', 'toward'):
        x = R[R.region == reg]
        print(f'\n===== {reg}: {len(x)} configs; both halves > 0: {x.both.mean():.3f}')
        for col in ('tp', 'sl', 'mo', 'N', 'fresh', 'sgate', 'mode'):
            print(x.groupby(col).agg(both=('both', 'mean'), med=('pd_tr', 'median'), med_minh=('minh', 'median'), best=('minh', 'max')).round(2).T.to_string())
        print(x.groupby(['be_trig', 'be_lock', 'trail']).agg(both=('both', 'mean'), med=('pd_tr', 'median'), best=('minh', 'max')).round(2).to_string())
        print('top 15 by min-half:')
        print(x.sort_values('minh', ascending=False)[c].head(15).round(2).to_string(index=False))
