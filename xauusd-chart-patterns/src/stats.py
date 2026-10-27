import json, numpy as np, pandas as pd, sys
from detect import load, atr
R = json.load(open('patterns.json'))
rng = np.random.default_rng(7)
frames = {}
def sim(h, l, c, i0, d, stop_d, tgt_d, horizon):
    e = c[i0]; st = e - d*stop_d; tg = e + d*tgt_d
    for i in range(i0+1, min(len(c), i0+1+horizon)):
        if (d==1 and l[i]<=st) or (d==-1 and h[i]>=st): return -1.0, 0
        if (d==1 and h[i]>=tg) or (d==-1 and l[i]<=tg): return tgt_d/stop_d, 1
    return (c[min(len(c)-1, i0+horizon)]-e)*d/stop_d, 0.5
rows = []
COST = 0.40
for r in R:
    o = r.get('out')
    if not o: continue
    tf = r['tf']
    if tf not in frames:
        df = load(tf); frames[tf] = (df.high.values, df.low.values, df.close.values, atr(df))
    h, l, c, a = frames[tf]
    i0 = o['i0']; risk = o['risk']; rew = o['rr']*risk
    if i0 + o['horizon'] >= len(c): continue
    # baseline: 20 random bars, same direction, stop/target scaled by ATR there
    bR = []
    for _ in range(20):
        j = int(rng.integers(50, len(c)-o['horizon']-1))
        s = a[j]/a[i0]
        Rb, _ = sim(h, l, c, j, r['dir'], risk*s, rew*s, o['horizon'])
        bR.append(Rb - COST/(risk*s))
    rows.append(dict(kind=r['kind'], tf=tf, R=o['R'] - COST/risk, hit=o['hit'], base=np.mean(bR), rr=o['rr']))
df = pd.DataFrame(rows)
g = df.groupby('kind').agg(n=('R','size'), target_first=('hit', lambda x: (x==1).mean()), stop_first=('hit', lambda x: (x==0).mean()),
                           avgR=('R','mean'), baseR=('base','mean'), rr=('rr','median'))
g['edge'] = g.avgR - g.baseR
print(g.round(2).sort_values('edge').to_string())
tot = df.agg({'R':'mean','base':'mean'}); print('ALL', len(df), tot.round(3).to_dict(), 'target first', round((df.hit==1).mean(),3))
print(df.groupby('tf')[['R','base']].mean().round(3))
out = {k: dict(n=int(v.n), target=round(float(v.target_first),3), stop=round(float(v.stop_first),3), avgR=round(float(v.avgR),3),
               baseR=round(float(v.baseR),3), rr=round(float(v.rr),2)) for k, v in g.iterrows()}
out['_all'] = dict(n=len(df), avgR=round(float(df.R.mean()),3), baseR=round(float(df.base.mean()),3), target=round(float((df.hit==1).mean()),3))
json.dump(out, open('stats.json','w'))
