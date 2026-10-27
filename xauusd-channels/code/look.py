import sys, numpy as np, pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, "/mnt/project-files/xauusd-github-bots/code")
import gbt, seg
tf, n, end, L, buf, ratio, K = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[8])
d = gbt.load(tf).iloc[-end-n:len(gbt.load(tf))-end if end else None]
o,h,l,c = [d[k].values for k in ('open','high','low','close')]
segs, ev = seg.segment(o,h,l,c,L,buf,ratio,k=K)
fig, ax = plt.subplots(figsize=(18,7))
x = np.arange(len(c))
ax.vlines(x, l, h, color='#999', lw=0.6); ax.plot(x, c, color='k', lw=0.5)
col = {1:'tab:green', -1:'tab:red', 0:'tab:blue'}
for s,e,lab in segs:
    b,a0,up,lo = seg.fit(c,h,l,s,e); xx = np.arange(s,e+1); ln = a0 + b*(xx-s)
    if lab == 0:
        ax.fill_between(xx, l[s:e+1].min(), h[s:e+1].max(), color=col[0], alpha=.12)
    else:
        ax.fill_between(xx, ln+lo, ln+up, color=col[lab], alpha=.15)
        ax.plot(xx, ln+up, color=col[lab], lw=1); ax.plot(xx, ln+lo, color=col[lab], lw=1)
ax.set_title(f'{tf} last {n} bars, {len(segs)} segments, L={L} buf={buf} ratio={ratio} k={K}  ({d.index[0]} - {d.index[-1]})')
plt.tight_layout(); plt.savefig(sys.argv[7], dpi=80)
from collections import Counter
print(len(segs), Counter(s[2] for s in segs), np.mean([e-s for s,e,_ in segs]))
