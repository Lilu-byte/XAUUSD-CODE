"""Stage 2a (TRAIN only): tradeable time-exit versions under the EA's entry rules (next-bar open, spread filter,
FAIR fills, base spread). Pure time exit (TP 1000) with a wide disaster stop, position caps and cooldowns."""
import sys, itertools, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from sb import *
from multiprocessing import Pool

TH = {'atr': [2.5, 3, 3.5, 4, 5], 'usd': [4, 5, 6, 8, 10]}
SIGS = [(k, mode, th, gate, fresh, sg) for k, mode, gate, fresh, sg in
        itertools.product((1, 2, 3), ('atr', 'usd'), ('none', 'away', 'toward'), (False, True), (0.0, 0.15)) for th in TH[mode]]
EXITS = list(itertools.product((2, 3, 4, 5, 6, 8, 10, 12, 15), (10.0, 25.0), (1, 3, 5), (0, 3)))
G = {}


def init():
    m, H = load_train(); G['m'] = m; G['H'] = H; G['f'] = feats(m)


def job(sd):
    k, mode, th, gate, fresh, sg = sd
    s = fade_signal(G['f'], k, mode, th, gate, fresh, sg)
    out = []
    for N, sl, mo, cd in EXITS:
        d, t = G['H'].run_x(s, (1000.0,), sl, N, mo, cd)
        r = halves(d, t)
        r.update(k=k, mode=mode, th=th, gate=gate, fresh=fresh, sgate=sg, N=N, sl=sl, mo=mo, cd=cd)
        out.append(r)
    return out


if __name__ == '__main__':
    t0 = time.time()
    with Pool(4, initializer=init) as p:
        rows = sum(p.map(job, SIGS, chunksize=4), [])
    R = pd.DataFrame(rows)
    R.to_csv(FAM + 's2_scan_train.csv.gz', index=False)
    R['both'] = (R.pd_A > 0) & (R.pd_B > 0)
    R['minh'] = R[['pd_A', 'pd_B']].min(axis=1)
    print('configs', len(R), 'signals', len(SIGS), 'exit settings', len(EXITS), 'secs %.0f' % (time.time() - t0))
    print('share per_day>0:', round((R.pd_tr > 0).mean(), 3), ' both halves>0:', round(R.both.mean(), 3),
          ' per_day>=5 both halves>=2.5:', round(((R.pd_tr >= 5) & (R.minh >= 2.5)).mean(), 4))
    pd.set_option('display.width', 250)
    print('\nboth-halves>0 share and best min-half by k x gate:')
    print(R.groupby(['k', 'gate']).agg(both=('both', 'mean'), best_minh=('minh', 'max'), med_pd=('pd_tr', 'median')).round(3).to_string())
    print('\nby N (both share, median per_day):')
    print(R.groupby('N').agg(both=('both', 'mean'), med=('pd_tr', 'median'), best=('minh', 'max')).round(3).T.to_string())
    print('\nby max_open x cooldown:')
    print(R.groupby(['mo', 'cd']).agg(both=('both', 'mean'), med=('pd_tr', 'median'), best=('minh', 'max')).round(3).to_string())
    print('\nby sl / fresh / sgate:')
    for c in ('sl', 'fresh', 'sgate'):
        print(R.groupby(c).agg(both=('both', 'mean'), med=('pd_tr', 'median'), best=('minh', 'max')).round(3).to_string())
    c = ['k', 'mode', 'th', 'gate', 'fresh', 'sgate', 'N', 'sl', 'mo', 'cd', 'pd_tr', 'pd_A', 'pd_B', 'tpd_tr', 'pt_tr', 'win_tr', 'wd_tr', 'dd_tr', 'ls_tr']
    print('\ntop 30 by min-half per_day:')
    print(R.sort_values('minh', ascending=False)[c].head(30).round(2).to_string(index=False))
    for g in ('none', 'away', 'toward'):
        print(f'\ntop 8 gate={g} by min-half:')
        print(R[R.gate == g].sort_values('minh', ascending=False)[c].head(8).round(2).to_string(index=False))
