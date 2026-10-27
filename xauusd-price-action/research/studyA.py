import numpy as np, pandas as pd, lightgbm as lgb, warnings
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
warnings.filterwarnings('ignore')
from feats import *
d=load('XAUUSD_D1'); F=bar_feats(d)
res=[]
for H in (1,5,20):
    y=(d.c.shift(-H)>d.c).astype(float); y[d.c.shift(-H).isna()]=np.nan
    X=F.copy(); ok=X.notna().all(1)&y.notna()
    for Y in range(2012,2027):
        # train strictly before Y, with an H-day embargo so labels don't overlap the test year
        tr=ok&(X.index<pd.Timestamp(f'{Y}-01-01')-pd.Timedelta(days=2*H)); te=ok&(X.index.year==Y)
        if te.sum()==0: continue
        m1=lgb.LGBMClassifier(n_estimators=200,learning_rate=0.03,num_leaves=8,min_child_samples=50,subsample=0.8,subsample_freq=1,colsample_bytree=0.7,verbose=-1).fit(X[tr],y[tr])
        m2=make_pipeline(StandardScaler(),LogisticRegression(C=0.1,max_iter=500)).fit(X[tr],y[tr])
        p1=m1.predict_proba(X[te])[:,1]; p2=m2.predict_proba(X[te])[:,1]
        # confidence thresholds from the training set's own predictions (no test peeking)
        ptr=m1.predict_proba(X[tr])[:,1]; c_tr=np.abs(ptr-0.5)
        q=dict(top20=np.quantile(c_tr,0.8),top10=np.quantile(c_tr,0.9))
        res.append(pd.DataFrame(dict(H=H,yr=Y,y=y[te].values,p_gbm=p1,p_lr=p2,base=float(y[tr].mean()>0.5),q20=q['top20'],q10=q['top10']),index=X.index[te]))
R=pd.concat(res); R.to_pickle('A_preds.pkl')
for H,g in R.groupby('H'):
    acc=lambda p: ((p>0.5)==(g.y==1)).mean()
    print(f"\nH={H}d ahead  n={len(g)}  always-up {100*g.y.mean():.1f}% | GBM {100*acc(g.p_gbm):.1f}% | logistic {100*acc(g.p_lr):.1f}%")
    for lab,qc in (('top20%',g.q20),('top10%',g.q10)):
        s=np.abs(g.p_gbm-0.5)>=qc
        print(f"   GBM confident {lab}: acc {100*((g.p_gbm[s]>0.5)==(g.y[s]==1)).mean():.1f}% on {s.mean()*100:.0f}% of days (n={s.sum()}), up-rate in those {100*g.y[s].mean():.0f}%")
    # simple trend rule for comparison
