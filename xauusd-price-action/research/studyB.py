import numpy as np, pandas as pd
from feats import load
h1=load('XAUUSD_H1'); r=h1.c-h1.o
df=pd.DataFrame(dict(up=(r>0).astype(int),r=r,hr=h1.index.hour,dow=h1.index.dayofweek,yr=h1.index.year))
df=df[r!=0]
rows=[]
for Y in range(2018,2027):
    tr=df[df.yr<Y]; te=df[df.yr==Y]
    stats=tr.groupby('hr').up.agg(['mean','size'])
    for thr in (0.52,0.54):
        good=stats[(stats['mean']>thr)|(stats['mean']<1-thr)]
        x=te[te.hr.isin(good.index)]
        pred=np.where(stats.loc[x.hr,'mean'].values>0.5,1,0)
        rows.append(dict(yr=Y,thr=thr,n=len(x),acc=(pred==x.up.values).mean(),cover=len(x)/len(te)))
R=pd.DataFrame(rows)
for thr,g in R.groupby('thr'):
    print(f"hour-of-day drift, train up-rate beyond {thr}: acc {100*np.average(g.acc,weights=g.n):.1f}% on {100*g.cover.mean():.0f}% of hours (n={g.n.sum()}); by year {dict(zip(g.yr,(100*g.acc).round(0)))}")
# lead-lag EURUSD -> XAU on M15
x=load('XAUUSD_M15'); e=load('EURUSD_M15')
j=pd.concat([np.log(x.c).diff().rename('x'),np.log(e.c).diff().rename('e')],axis=1).dropna()
j['xn']=j.x.shift(-1)
j=j.dropna(); big=j.e.abs()>j.e.abs().quantile(0.9)
print(f"EURUSD M15 move -> next XAU M15 same sign: all {100*(np.sign(j.e)==np.sign(j.xn)).mean():.1f}%, biggest 10% EUR moves {100*(np.sign(j.e[big])==np.sign(j.xn[big])).mean():.1f}% (n={big.sum()})")
print(f"XAU M15 own momentum next bar: {100*(np.sign(j.x)==np.sign(j.xn)).mean():.1f}%")
