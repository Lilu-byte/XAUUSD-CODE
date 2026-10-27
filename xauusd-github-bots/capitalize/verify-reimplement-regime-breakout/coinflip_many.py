"""Coin-flip with 500 runs over 5 seeds, same signal bars and exits, random direction."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-reimplement-regime-breakout')
from indep import load, indicators, run, daily
h = load('/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv'); d1 = load('/mnt/project-files/xauusd-price-action/data/XAUUSD_D1.csv')
alld = pd.DatetimeIndex(np.unique(h.index.normalize())); te = alld[alld >= '2022-01-01']; tr = alld[alld < '2022-01-01']
ind = indicators(h, d1); t, _ = run(h, ind); pte = daily(t, te).mean(); ptr = daily(t, tr).mean()
c = ind['c']; reg = ind['reg']
sb = ((c > ind['hh']) & (reg > 0)) | ((c < ind['ll']) & (reg < 0))
# also ungated signal bars (both breakouts), random direction
sb2 = (c > ind['hh']) | (c < ind['ll'])
for lab, bars in (('gated bars', sb), ('all breakout bars', sb2)):
    te_r, tr_r = [], []
    for seed in range(5):
        rng = np.random.default_rng(seed)
        for r in range(100):
            s = np.zeros(len(c)); s[bars] = np.where(rng.random(bars.sum()) < .5, 1, -1)
            x, _ = run(h, ind, sig=s); te_r.append(daily(x, te).mean()); tr_r.append(daily(x, tr).mean())
    te_r, tr_r = np.array(te_r), np.array(tr_r)
    print(f'{lab}: test median {np.median(te_r):.2f} (5-95% {np.percentile(te_r,5):.2f}..{np.percentile(te_r,95):.2f}), pick {pte:.2f} beats {np.mean(pte > te_r)*100:.0f}% | '
          f'train median {np.median(tr_r):.2f}, pick {ptr:.2f} beats {np.mean(ptr > tr_r)*100:.0f}%')
