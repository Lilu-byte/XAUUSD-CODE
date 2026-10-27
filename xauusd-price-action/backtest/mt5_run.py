import sys
sys.path.insert(0,'/home/claude/bt')
from pa_backtest import *
D='/home/claude/data/mt5/x/XAU_Export/'
def load(tf):
    df=pd.read_csv(D+f'XAUUSD_{tf}.csv')
    df.index=pd.to_datetime(df.time,format='%Y.%m.%d %H:%M')
    return df.rename(columns=dict(open='o',high='h',low='l',close='c'))[['o','h','l','c','spread']]
h1,h4,d1=load('H1'),load('H4'),load('D1')
print("H1 gaps>4d:",(h1.index.to_series().diff()>pd.Timedelta(days=4)).sum(), "median spread $",h1.spread.median()*0.01)
h4=h4[h4.index>='2016-01-01']; d1=d1[d1.index>='2015-01-01']
h1.to_pickle('mt5_h1.pkl'); h4.to_pickle('mt5_h4.pkl'); d1.to_pickle('mt5_d1.pkl')
cfgs={"rules as written":dict(k_h4=2,k_d1=2,tol=0.5,max_range_pos=0.5),
      "tuned":dict(k_h4=3,k_d1=2,tol=1.0,max_range_pos=0.5)}
for name,c in cfgs.items():
    s=find_setups(h4,d1,**c)
    s=s[s.time>='2016-08-01']
    if name=='tuned':
        s=ltf_confirm(s,h1,h4); s=s[s.pattern.str.contains('engulf')]
    r=score(s,h1)
    r.to_csv(f'mt5_trades_{name.split()[0]}.csv',index=False)
    print(f"\n== {name}")
    for lab,x in (("2016-08..2019-02",r[r.time<'2019-03-01']),("2019-03..2026-10 (new)",r[r.time>='2019-03-01']),("all",r)):
        summarize(x,lab)
    new=r[r.time>='2019-03-01']
    if name=='tuned':
        for g in "AB": summarize(new[new.grade==g],f"   new, grade {g}")
        new=new.assign(yr=new.time.dt.year)
        print(new.groupby('yr').agg(n=('win_1R','size'),w1=('win_1R','mean'),w2=('win_2R','mean')).round(2).T.to_string())
    print("   median risk $",round(new.risk.median(),2))
# baseline on new period
S4=structure(h4,2); SD=structure(d1,2)
di=np.searchsorted((d1.index+pd.Timedelta(days=1)).values,(h4.index+pd.Timedelta(hours=4)).values,side='right')-1
avg=pd.Series(h4.h.values-h4.l.values).rolling(20).mean().shift(1).values
rows=[]
for j in range(25,len(h4)-1,3):
    if h4.index[j]<pd.Timestamp('2019-03-01'): continue
    tr=S4['trend'][j]
    if tr==0 or SD['trend'][di[j]]!=tr or np.isnan(avg[j]): continue
    e=h4.c.values[j]; R=1.1*avg[j]
    rows.append(dict(time=h4.index[j],close_time=h4.index[j]+pd.Timedelta(hours=4),dir=tr,entry=e,invalidation=e-tr*R,risk=R))
summarize(score(pd.DataFrame(rows),h1),"BASELINE 2019-2026 trend only")
