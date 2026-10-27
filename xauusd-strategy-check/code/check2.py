import sys; sys.path.insert(0,'/mnt/project-files/xauusd-strategy-check/code')
from load import *; from bt import *
d=mt5(); c=d.close; S='2005-04-01'
print('MA length sweep (with volsize), close exec, today swap')
rows=[]
for n in [20,50,75,100,125,150,175,200,225,250,300]:
    p=ma_rule(c,n)*volsize(c); rows.append(stats(run(d,p)[S:],p[S:],f'MA{n}'))
print(pd.DataFrame(rows).to_string(index=False))
print('vol target / cap sweep with MA200')
rows=[]
for t in [0.10,0.15,0.20]:
  for cap in [1.0,1.5,2.0]:
    p=ma_rule(c)*volsize(c,t,cap); rows.append(stats(run(d,p)[S:],p[S:],f'tgt{t} cap{cap}'))
print(pd.DataFrame(rows).to_string(index=False))
print('sub-periods')
P={'B&H':pd.Series(1.0,index=c.index),'proposed':ma_rule(c)*volsize(c)}
for a,b in [('2005-04','2012-12'),('2013-01','2018-12'),('2019-01','2026-10')]:
    print(a,b,[ (k,stats(run(d,p)[a:b])['cagr'],stats(run(d,p)[a:b])['sharpe'],stats(run(d,p)[a:b])['maxdd']) for k,p in P.items()])
print('per-year')
yr=pd.DataFrame({k:(1+run(d,p)[S:]).groupby(lambda x:x.year).prod()-1 for k,p in P.items()}).round(3)*100
print(yr.T.to_string())
# block bootstrap of Sharpe difference proposed - B&H
r1=run(d,P['proposed'])[S:]; r0=run(d,P['B&H'])[S:]; rng=np.random.default_rng(0); n=len(r1); B=63; diffs=[]
for _ in range(2000):
    idx=np.concatenate([np.arange(s,min(s+B,n)) for s in rng.integers(0,n,n//B+1)])[:n]
    a=r1.values[idx]; b=r0.values[idx]; diffs.append(a.mean()/a.std()-b.mean()/b.std())
diffs=np.array(diffs)*np.sqrt(252); print('Sharpe diff proposed-B&H: mean %.2f, 90%% CI [%.2f, %.2f], P(diff<=0)=%.2f'%(diffs.mean(),*np.percentile(diffs,[5,95]),(diffs<=0).mean()))
# OANDA replication
o=oanda(); co=o.close; So='2007-01-01'
print('OANDA 2007-2019-02 vs MT5 same span')
for nm,dd_ in [('oanda',o),('mt5',d)]:
    cc=dd_.close
    for k,p in {'B&H':pd.Series(1.0,index=cc.index),'proposed':ma_rule(cc)*volsize(cc)}.items():
        print(nm,stats(run(dd_,p)[So:'2019-02-25'],p,k))
