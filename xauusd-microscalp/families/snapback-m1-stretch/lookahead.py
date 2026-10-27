"""Truncation test: recompute the three pick signals on data cut right after bar i, for 300 random i
(TRAIN and TEST), and compare with the full-data signal at i. Expect 0 mismatches."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch')
from feats import *
from multiprocessing import Pool

onset = lambda s0: np.where(np.r_[0, s0[:-1]] == s0, 0, s0)


def picks(m):
    f = features(m); v = valid(m, f)
    run = onset(sig_run(f, 4, 4)); rz = both(sig_rsi(f, 3, 97.5), sig_z(f, 60, 2))
    out = np.vstack([run, rz, union(run, onset(rz))])
    return np.where(v, out, 0)


M = load_m1()


def one(i):
    return picks(M.iloc[:i + 1])[:, -1]


if __name__ == '__main__':
    full = picks(M)
    rng = np.random.default_rng(7)
    # half the probes at bars where some pick fires (the cases that matter), half anywhere
    fire = np.where((full != 0).any(axis=0))[0]
    idx = np.r_[rng.choice(fire[fire > 300], 150, replace=False), rng.integers(300, len(M) - 1, 150)]
    with Pool(4) as p:
        res = p.map(one, idx.tolist())
    trunc = np.array(res).T
    mism = (trunc != full[:, idx]).sum(axis=1)
    print(f'{len(idx)} truncation points ({(full[:, idx] != 0).any(axis=0).sum()} with a signal); mismatches per pick (P1, P2, P3): {mism.tolist()}')
