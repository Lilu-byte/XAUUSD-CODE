import numpy as np, pandas as pd, sys
sys.path.insert(0,'/home/claude/bt')
from pa_backtest import structure
D='/home/claude/data/mt5/x/XAU_Export/'
def load(name):
    df=pd.read_csv(D+name+'.csv'); df.index=pd.to_datetime(df.time,format='%Y.%m.%d %H:%M')
    return df.rename(columns=dict(open='o',high='h',low='l',close='c'))[['o','h','l','c']]
def bar_feats(b, k_struct=2, prefix=''):
    f=pd.DataFrame(index=b.index); c=b.c; r=np.log(c).diff()
    rng=(b.h-b.l); avg=rng.rolling(20).mean()
    for n in (1,2,3,5,10,20,60,120,250):
        f[f'ret{n}']=np.log(c/c.shift(n))/ (r.rolling(60).std()*np.sqrt(n))
    f['rng_rel']=rng/avg; f['body']=(c-b.o)/rng.replace(0,np.nan); f['closepos']=(c-b.l)/rng.replace(0,np.nan)
    f['upwick']=(b.h-np.maximum(b.o,c))/rng.replace(0,np.nan); f['lowick']=(np.minimum(b.o,c)-b.l)/rng.replace(0,np.nan)
    for n in (20,60,250):
        hi=b.h.rolling(n).max(); lo=b.l.rolling(n).min(); f[f'pos{n}']=(c-lo)/(hi-lo)
    f['vol_regime']=r.rolling(20).std()/r.rolling(250).std()
    f['gap']=(b.o-c.shift())/avg
    up=(c>c.shift()).astype(int); f['streak']=up.groupby((up!=up.shift()).cumsum()).cumcount()+1; f['streak']*=np.where(up==1,1,-1)
    S=structure(b,k_struct); f['struct_trend']=S['trend']; f['dist_sh']=(c-S['last_sh'])/avg; f['dist_sl']=(c-S['last_sl'])/avg
    f['dow']=b.index.dayofweek
    return f.add_prefix(prefix)
