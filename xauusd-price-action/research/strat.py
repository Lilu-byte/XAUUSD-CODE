import numpy as np, pandas as pd, sys
sys.path.insert(0,'/home/claude/bt')
from feats import load
from pa_backtest import structure
d=load('XAUUSD_D1'); c=d.c
ret=c.pct_change().fillna(0)
# costs: half-spread-ish 0.35$ per side on entry/exit, swap long ~0.126$/oz/night, short ~0.046$/oz/night (from the export's info file)
spread=0.35/4195; swapL=0.126/4195; swapS=0.046/4195  # fractions of price, from today's 0.35$ spread and 0.126$/0.046$ per oz per night
def run(pos,name):
    pos=pos.shift(1).fillna(0)  # decide at close, hold from next bar: no lookahead
    turn=pos.diff().abs().fillna(0)
    cost=turn*spread + np.where(pos>0,swapL*pos.abs(),np.where(pos<0,swapS*pos.abs(),0))
    r=(pos*ret-cost).fillna(0)
    eq=(1+r).cumprod()
    def stats(rr):
        e=(1+rr).cumprod(); yrs=len(rr)/252
        cagr=e.iloc[-1]**(1/yrs)-1; dd=(e/e.cummax()-1).min(); sh=rr.mean()/rr.std()*np.sqrt(252) if rr.std()>0 else 0
        return f"CAGR {100*cagr:5.1f}%  maxDD {100*dd:6.1f}%  Sharpe {sh:4.2f}"
    per={p:stats(r[(r.index>=a)&(r.index<b)]) for p,(a,b) in {"2004-12":("2004","2013"),"2013-18":("2013","2019"),"2019-26":("2019","2027")}.items()}
    print(f"{name:42s} ALL {stats(r)} | in mkt {100*(pos!=0).mean():3.0f}% | trades/yr {turn.sum()/2/ (len(r)/252):4.1f}")
    for k,v in per.items(): print(f"{'':44s}{k}: {v}")
    return r
sma=lambda n: c.rolling(n).mean()
volt=ret.rolling(20).std()*np.sqrt(252)
S=structure(d,2); st=pd.Series(S['trend'],index=d.index)
hi50=d.h.rolling(50).max().shift(1); lo20=d.l.rolling(20).min().shift(1)
don=pd.Series(0.0,index=d.index); p=0
for i in range(len(d)):
    if p==0 and c.iloc[i]>hi50.iloc[i]: p=1
    elif p==1 and c.iloc[i]<lo20.iloc[i]: p=0
    don.iloc[i]=p
runs={}
runs['buy&hold']=run(pd.Series(1.0,index=d.index),"1 Buy and hold")
runs['sma200']=run((c>sma(200)).astype(float),"2 Long only when close > 200-day avg")
runs['struct_long']=run((st==1).astype(float),"3 Long only when Daily structure bullish")
runs['struct_ls']=run(st.astype(float),"4 Long/short with Daily structure")
runs['donchian']=run(don,"5 Long on 50-day high break, exit 20-day low")
# pullback within trend: above 200d avg and close is lowest of last 5 closes -> hold 5 days
sig=((c>sma(200))&(c<=c.rolling(5).min())).astype(float)
pb=sig.replace(0,np.nan).ffill(limit=4).fillna(0)
runs['pullback']=run(pb,"6 Buy 5-day-low pullbacks above 200-day avg, hold 5d")
# vol targeting on #2: scale to 15% annual vol, max 1.5x
w=(0.15/volt).clip(upper=1.5)
runs['sma200_vt']=run((c>sma(200)).astype(float)*w,"7 = #2 sized to 15% volatility")
pd.DataFrame(runs).to_pickle('strat_returns.pkl')
