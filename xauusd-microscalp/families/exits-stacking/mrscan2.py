"""Stage E (TRAIN only): full bracket neighbourhood of the mean-reversion signals with spread gates, to see whether the
best Stage-B MR cells are a stable region or isolated cells. max_open 1, cooldown 0, FAIR, base spread."""
from sigs2 import *
from multiprocessing import Pool
import itertools, time

TPS = [0.10, 0.20, 0.30, 0.50, 0.75, 1.00]
SLS = [1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0]
TOS = [1, 2, 3, 5, 10, 20, 30]
GATES = [None, 0.10, 0.15, 0.20]
G = {}


def init():
    m1, H = train_harness(); S = build(m1); tr = m1.index < SPLIT
    G['H'] = H; G['S'] = {(k, g): (S[k] if g is None else gate(S[k], m1, g))[tr] for k in ('MR', 'MR6') for g in GATES}


def job(a):
    s, g, tp, sl, to = a
    d, t = run_pw(G['H'], G['S'][(s, g)], tp, sl, timeout=to)
    r = summ(d, t, 'train')
    r.update(sig=s, gate=g if g else 0, tp=tp, sl=sl, timeout=to, avg_spr=t.spr.mean())
    r['resid'] = r['per_trade'] + r['avg_spr']
    return r


if __name__ == '__main__':
    t0 = time.time()
    jobs = list(itertools.product(['MR', 'MR6'], GATES, TPS, SLS, TOS))
    with Pool(4, initializer=init) as p:
        rows = p.map(job, jobs, chunksize=20)
    R = pd.DataFrame(rows)
    R.to_csv(OUT + 'mrscan2_train.csv', index=False)
    print('configs', len(R), 'secs %.0f' % (time.time() - t0))
    pd.set_option('display.width', 250)
    R['both'] = (R.pd_jul > 0) & (R.pd_aug > 0)
    print('share of cells with per_day > 0 / both halves > 0, by signal and gate:')
    print(R.groupby(['sig', 'gate']).agg(pos=('per_day', lambda x: (x > 0).mean()), both=('both', 'mean'),
                                         best=('per_day', 'max'), med_pt=('per_trade', 'median'), spr=('avg_spr', 'mean')).round(3))
    for s in ('MR', 'MR6'):
        for g in (0, 0.15):
            x = R[(R.sig == s) & (R.gate == g) & (R.sl == 20.0)].pivot(index='tp', columns='timeout', values='per_day')
            print(f'\n{s} gate {g} SL 20: per_day TP x timeout'); print(x.round(2).to_string())
    c = ['sig', 'gate', 'tp', 'sl', 'timeout', 'per_day', 'trades_day', 'pwin', 'per_trade', 'avg_spr', 'worst_day', 'max_dd', 'pd_jul', 'pd_aug']
    print('\ntop 15 both halves > 0:'); print(R[R.both].sort_values('per_day', ascending=False)[c].head(15).round(3).to_string(index=False))
