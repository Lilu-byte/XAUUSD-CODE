import pickle, sys
sys.path.insert(0,'/home/claude/bt')
from pa_backtest import *
h1,h4,d1=pickle.load(open('bars.pkl','rb'))
split=pd.Timestamp('2015-01-01')
t=h1.index.values; H=h1.h.values; L=h1.l.values
def curve(ss, mults=(0.5,0.75,1,1.5,2,3)):
    out={}
    for m in mults:
        w=[]
        for s in ss.itertuples():
            i0=np.searchsorted(t,np.datetime64(s.close_time)); tgt=s.entry+s.dir*m*s.risk; o=None
            for i in range(i0,min(i0+240,len(t))):
                if (L[i]<=s.invalidation) if s.dir==1 else (H[i]>=s.invalidation): o=0;break
                if (H[i]>=tgt) if s.dir==1 else (L[i]<=tgt): o=1;break
            if o is not None: w.append(o)
        w=np.array(w); out[m]=(w.mean(), m*w.mean()-(1-w.mean()), len(w))
    return out
def ci(p,n): 
    se=np.sqrt(p*(1-p)/n); return f"{100*p:.0f}% (95% range {100*(p-1.96*se):.0f}-{100*(p+1.96*se):.0f}%, n={n})"
cfgs={"default (all setups, k=2)":dict(k_h4=2,k_d1=2,tol=0.5,max_range_pos=0.5),
      "tuned (k_h4=3, H1 confirm, engulfing)":dict(k_h4=3,k_d1=2,tol=1.0,max_range_pos=0.5)}
for name,c in cfgs.items():
    s=find_setups(h4,d1,**c)
    if 'tuned' in name:
        s=ltf_confirm(s,h1,h4); s=s[s.pattern.str.contains('engulf')]
    r=score(s,h1)
    r['spread_R']=0.36/r.risk
    print(f"\n== {name}: n={len(r)}, median risk ${r.risk.median():.2f}, spread cost {r.spread_R.median():.3f}R")
    for lab,x in (("2006-2014",r[r.time<split]),("2015-2019",r[r.time>=split]),("all",r)):
        print(f"  {lab}: 1R {ci(x.win_1R.mean(),len(x))} | dir 1d {100*x.dir_1d.mean():.0f}% | 5d {100*x.dir_5d.mean():.0f}%")
    for m,(w,ev,n) in curve(r).items():
        print(f"    target {m}R: win {100*w:.1f}%  expectancy {ev:+.2f}R before spread (n={n})")
    r.to_csv(f"/home/claude/bt/trades_{'tuned' if 'tuned' in name else 'default'}.csv",index=False)
