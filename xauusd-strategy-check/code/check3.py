import sys; sys.path.insert(0,'/mnt/project-files/xauusd-strategy-check/code')
from load import *; from bt import *
d=mt5(); c=d.close; S='2005-04-01'
def dd_info(r):
    eq=(1+r).cumprod(); dd=eq/eq.cummax()-1; t=dd.idxmin(); pk=eq[:t].idxmax(); return pk.date(),t.date(),round(dd.min()*100,1)
p=ma_rule(c)*volsize(c); r=run(d,p)
print('worst DD 2019+:',dd_info(r['2019':]), 'overall', dd_info(r[S:]))
eq=(1+r[S:]).cumprod(); dd=eq/eq.cummax()-1
print('DD now (proposed)',round(dd.iloc[-1]*100,1)); eqb=(1+run(d,pd.Series(1.0,index=c.index))[S:]).cumprod(); print('DD now B&H',round((eqb/eqb.cummax()-1).iloc[-1]*100,1))
print('what a $3,000 account can actually run: 0 or 0.01 lot = ~1.4x equity')
for lev in [1.0,1.4]:
    pb=ma_rule(c)*lev
    for fin in ['today','ffr']: print(lev,fin,stats(run(d,pb,fin=fin)[S:],pb[S:],f'MA200 binary {lev}x'))
pb=pd.Series(1.4,index=c.index); print(stats(run(d,pb)[S:],pb[S:],'B&H 1.4x'))
# Fair comparison: B&H scaled to proposed vol
print(stats(run(d,pd.Series(13.4/17.9,index=c.index))[S:],None,'B&H at 0.75x (same vol as proposed)'))
