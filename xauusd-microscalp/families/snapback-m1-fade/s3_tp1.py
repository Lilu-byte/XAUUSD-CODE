"""Stage 3 (TRAIN only): versions inside David's rule (every position closes at a TP of $1 or less, or by its
stop / time limit), on the two signal regions found in stage 2.
 (a) re-entry ladder (_simlad): rung 1 at the next open after the spike; each time a rung's TP fills while the price
     is still stretched (snap-back recovered less than lad_q of the spike, measured from the pre-spike close
     close[i-3]), open the next rung (mode 0: next bar open; mode 1: at once at the TP price), up to lad_max rungs,
     within lad_window bars of the signal. lad_max 1 = a plain single TP.
 (b) several 0.01 legs on one signal with staggered TPs and a common stop / time exit (_simx with several legs).
Spread is paid on every position: base model (bar spread + $0.05), FAIR fills, EA entry rules."""
import sys, itertools, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from sb import *
from multiprocessing import Pool

SIGDEFS = {'snap_atr3.5': (3, 'atr', 3.5, 'none', False, 0.0), 'snap_usd8': (3, 'usd', 8.0, 'none', False, 0.0),
           'tow_atr2.5': (3, 'atr', 2.5, 'toward', False, 0.0), 'tow_atr3': (3, 'atr', 3.0, 'toward', False, 0.0)}
LAD = list(itertools.product((0.5, 0.75, 1.0), (5.0, 10.0, 15.0), (3, 5, 10, 15), (1, 3, 6, 10), (0.5, 1.0, 1.5), (10, 30), (0, 1)))
LEGS = list(itertools.product(((0.25, 0.5, 1.0), (0.5, 1.0), (0.5, 0.75, 1.0), (1.0,)), (5.0, 10.0, 15.0), (3, 5, 10, 15), (1, 2)))
G = {}


def init():
    m, H = load_train(); G['m'] = m; G['H'] = H; G['f'] = feats(m)


def job(a):
    name, kind, chunk = a
    f = G['f']; s = fade_signal(f, *SIGDEFS[name]); lvl = f.p3.values
    out = []
    for p in chunk:
        if kind == 'lad':
            tp, sl, to, lm, q, w, md = p
            if lm == 1 and (q != 1.0 or w != 30 or md != 0): continue      # lad_max 1 ignores the ladder settings
            d, t = G['H'].run_lad(s, lvl, tp, sl, to, lm, q, w, md)
            r = halves(d, t); r.update(sig=name, kind='lad', tp=tp, sl=sl, to=to, lad_max=lm, lad_q=q, lad_window=w, mode=md,
                                      rungs=t.rung.mean(), tpshare=(t.kind == 0).mean())
        else:
            tps, sl, to, mb = p
            d, t = G['H'].run_x(s, tps, sl, to, len(tps) * mb, 0)
            r = halves(d, t); r.update(sig=name, kind='legs', tp='/'.join(map(str, tps)), sl=sl, to=to, lad_max=mb,
                                      tpshare=(t.kind == 0).mean())
        out.append(r)
    return out


if __name__ == '__main__':
    t0 = time.time()
    jobs = []
    for name in SIGDEFS:
        for i in range(0, len(LAD), 72): jobs.append((name, 'lad', LAD[i:i + 72]))
        jobs.append((name, 'legs', LEGS))
    with Pool(4, initializer=init) as p:
        rows = sum(p.map(job, jobs, chunksize=1), [])
    R = pd.DataFrame(rows)
    R.to_csv(FAM + 's3_tp1_train.csv.gz', index=False)
    R['minh'] = R[['pd_A', 'pd_B']].min(axis=1); R['both'] = R.minh > 0
    print('configs', len(R), '(ladder', (R.kind == 'lad').sum(), ', legs', (R.kind == 'legs').sum(), ') secs %.0f' % (time.time() - t0))
    pd.set_option('display.width', 250)
    c = ['sig', 'kind', 'tp', 'sl', 'to', 'lad_max', 'lad_q', 'lad_window', 'mode', 'pd_tr', 'pd_A', 'pd_B', 'tpd_tr', 'pt_tr', 'win_tr',
         'wd_tr', 'dd_tr', 'rungs', 'tpshare', 'ls_tr']
    for kind in ('lad', 'legs'):
        x = R[R.kind == kind]
        print(f'\n===== {kind}: {len(x)} configs; both halves > 0: {x.both.mean():.3f}; per_day > 0: {(x.pd_tr > 0).mean():.3f}')
        print(x.groupby('sig').agg(both=('both', 'mean'), med=('pd_tr', 'median'), best=('pd_tr', 'max'), best_minh=('minh', 'max')).round(2).to_string())
        cols = ('tp', 'sl', 'to', 'lad_max', 'lad_q', 'lad_window', 'mode') if kind == 'lad' else ('tp', 'sl', 'to', 'lad_max')
        for col in cols:
            print(x.groupby(col).agg(both=('both', 'mean'), med=('pd_tr', 'median'), best=('minh', 'max')).round(2).T.to_string())
        print('top 12 by min-half:')
        print(x.sort_values('minh', ascending=False)[c].head(12).round(2).to_string(index=False))
    # ladder vs single TP: same signal / tp / sl / to
    x = R[(R.kind == 'lad')]
    one = x[x.lad_max == 1].set_index(['sig', 'tp', 'sl', 'to']).pd_tr
    best = x[x.lad_max > 1].groupby(['sig', 'tp', 'sl', 'to']).pd_tr.max()
    print('\nladder best (over lad settings) minus single TP, same sig/tp/sl/to: median %+.2f, share > 0 %.2f' %
          ((best - one).median(), ((best - one) > 0).mean()))
