import pickle, sys, itertools
sys.path.insert(0,'/home/claude/bt')
from pa_backtest import *
h1,h4,d1=pickle.load(open('bars.pkl','rb'))
split=pd.Timestamp('2015-01-01')
rows=[]
for kh,kd,tol,pos in itertools.product((2,3),(2,3),(0.25,0.5,1.0),(0.33,0.5,0.75)):
    s=find_setups(h4,d1,k_h4=kh,k_d1=kd,tol=tol,max_range_pos=pos)
    if not len(s): continue
    for conf in (False,True):
        ss=ltf_confirm(s,h1,h4) if conf else s
        if not len(ss): continue
        r=score(ss,h1)
        for filt in ("all","sweep","engulf","sweep+engulf"):
            x=r
            if 'sweep' in filt: x=x[x.sweep]
            if 'engulf' in filt: x=x[x.pattern.str.contains('engulf')]
            tr,te=x[x.time<split],x[x.time>=split]
            rows.append(dict(kh=kh,kd=kd,tol=tol,pos=pos,conf=conf,filt=filt,
              n_tr=len(tr),tr1R=tr.win_1R.mean(),tr2R=tr.win_2R.mean(),
              n_te=len(te),te1R=te.win_1R.mean(),te2R=te.win_2R.mean()))
g=pd.DataFrame(rows); g.to_pickle('grid.pkl')
print("configs:",len(g))
top=g[g.n_tr>=40].sort_values('tr1R',ascending=False).head(12)
print(top.round(3).to_string())
print("\nbest train 1R overall:",g[g.n_tr>=40].tr1R.max(), " max test 1R among n_te>=20:",g[g.n_te>=20].te1R.max())
