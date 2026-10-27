import sys; sys.path.insert(0,'/mnt/project-files/xauusd-strategy-check/code')
from load import *; from bt import *
d=mt5(); c=d.close; S='2005-04-01'
def hyst(c,n=200,b=0.02):
    m=c.rolling(n).mean(); s=np.zeros(len(c)); st=0
    for i,(x,y) in enumerate(zip(c.values,m.values)):
        if np.isnan(y): s[i]=0; continue
        if st==0 and x>y*(1+b): st=1
        elif st==1 and x<y*(1-b): st=0
        s[i]=st
    return pd.Series(s,index=c.index)
def weekly(sig):
    fri=sig.index.to_series().dt.isocalendar().week.ne(sig.index.to_series().shift(-1).dt.isocalendar().week)
    return sig.where(fri).ffill().fillna(0)
def ens_ma(c,ns=(50,100,150,200,250)): return sum(ma_rule(c,n) for n in ns)/len(ns)
def tsmom(c,lbs=(21,63,126,252)): return sum((c>c.shift(l)).astype(float) for l in lbs)/len(lbs)
V=volsize(c); V60=volsize(c,n=60); Vew=(0.15/(np.log(c).diff().ewm(span=40).std()*np.sqrt(252))).clip(upper=1.5).fillna(0)
C={'0 proposed (MA200 x vol20)':ma_rule(c)*V,
   'A ensemble MA 50-250 x vol':ens_ma(c)*V,
   'B weekly MA200 x vol':weekly(ma_rule(c))*V,
   'C MA200 2% band x vol':hyst(c)*V,
   'D MA200, keep 1/3 when below':(ma_rule(c)*2/3+1/3)*V,
   'E 12m momentum x vol':(c>c.shift(252)).astype(float)*V,
   'F momentum ensemble 1-12m x vol':tsmom(c)*V,
   'G MA200 x vol60':ma_rule(c)*V60,
   'H MA200 x EWMA vol':ma_rule(c)*Vew,
   'I ens MA + weekly + vol60':weekly(ens_ma(c))*V60,
   'ref vol-size only':V,'ref B&H':pd.Series(1.0,index=c.index)}
rows=[]
for k,p in C.items():
    r=run(d,p); full=stats(r[S:],p[S:],k); h1=stats(r[S:'2015-12']); h2=stats(r['2016':]); rf=stats(run(d,p,fin='ffr')[S:])
    full.update(sh_05_15=h1['sharpe'],sh_16_26=h2['sharpe'],cagr_ffr=rf['cagr'],turnover=round(p[S:].diff().abs().sum()/(len(p[S:])/252),1))
    rows.append(full)
print(pd.DataFrame(rows).drop(columns=['calmar']).to_string(index=False))
def boot(ra,rb,B=63,N=2000):
    rng=np.random.default_rng(1); n=len(ra); out=[]
    for _ in range(N):
        idx=np.concatenate([np.arange(s,min(s+B,n)) for s in rng.integers(0,n,n//B+1)])[:n]
        a=ra.values[idx]; b=rb.values[idx]; out.append((a.mean()/a.std()-b.mean()/b.std())*np.sqrt(252))
    out=np.array(out); return round(out.mean(),2),np.round(np.percentile(out,[5,95]),2),round((out>0).mean(),2)
R={k:run(d,p)[S:] for k,p in C.items()}
for k in ['I ens MA + weekly + vol60','B weekly MA200 x vol','D MA200, keep 1/3 when below']:
    print(k,'vs proposed',boot(R[k],R['0 proposed (MA200 x vol20)']),'vs B&H',boot(R[k],R['ref B&H']))
print('I sensitivity:')
for ns in [(50,100,150,200,250),(100,150,200,250,300),(50,100,200),(20,50,100,200)]:
  for vn in [20,60,120]:
    p=weekly(ens_ma(c,ns))*volsize(c,n=vn); s=stats(run(d,p)[S:]); print(ns,vn,s['cagr'],s['sharpe'],s['maxdd'],s['lose_yrs'])
