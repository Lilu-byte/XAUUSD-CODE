import numpy as np, pandas as pd, lightgbm as lgb, warnings
warnings.filterwarnings('ignore')
from feats import *
h4=load('XAUUSD_H4'); d=load('XAUUSD_D1')
F=bar_feats(h4,k_struct=3,prefix='h4_'); F['hour']=h4.index.hour
FD=bar_feats(d,prefix='d_')
# daily features known at an H4 close = previous completed day
FD.index=FD.index+pd.Timedelta(days=1)
F=pd.merge_asof(F.sort_index(),FD.sort_index(),left_index=True,right_index=True,direction='backward')
out=[]
for H in (1,6):
    fwd=h4.c.shift(-H); y=(fwd>h4.c).astype(float); y[fwd.isna()]=np.nan
    ok=F.notna().all(1)&y.notna()
    for Y in range(2017,2027):
        tr=ok&(F.index<pd.Timestamp(f'{Y}-01-01')-pd.Timedelta(days=3)); te=ok&(F.index.year==Y)
        m=lgb.LGBMClassifier(n_estimators=300,learning_rate=0.03,num_leaves=16,min_child_samples=100,subsample=0.8,subsample_freq=1,colsample_bytree=0.6,verbose=-1).fit(F[tr],y[tr])
        p=m.predict_proba(F[te])[:,1]; ptr=m.predict_proba(F[tr])[:,1]; ctr=np.abs(ptr-0.5)
        out.append(pd.DataFrame(dict(H=H,y=y[te].values,p=p,q80=np.quantile(ctr,0.8),q95=np.quantile(ctr,0.95)),index=F.index[te]))
R=pd.concat(out)
for H,g in R.groupby('H'):
    acc=((g.p>0.5)==(g.y==1)).mean()
    print(f"H4 model, next {H} H4 candle(s): all {100*acc:.1f}% (n={len(g)}), always-up {100*g.y.mean():.1f}%")
    for lab,q in (('top20%',g.q80),('top5%',g.q95)):
        s=np.abs(g.p-0.5)>=q
        print(f"   confident {lab}: {100*((g.p[s]>0.5)==(g.y[s]==1)).mean():.1f}% on {100*s.mean():.0f}% of candles (n={s.sum()}), up-rate there {100*g.y[s].mean():.0f}%")
A=pd.read_pickle('A_preds.pkl')
for H,g in A.groupby('H'):
    c=np.abs(g.p_gbm-0.5); 
    for qq in (0.9,0.95,0.98):
        s=c>=c.quantile(qq)  # NOTE: test-set quantile, for the curve only
        print(f"daily H={H} top {100*(1-qq):.0f}% most confident (ex-post cut): {100*((g.p_gbm[s]>0.5)==(g.y[s]==1)).mean():.1f}% n={s.sum()}")
