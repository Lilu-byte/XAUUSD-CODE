import pandas as pd, numpy as np
# approximate annual avg effective fed funds rate (%), used for a realistic swap model
FFR={2004:1.35,2005:3.2,2006:4.97,2007:5.02,2008:1.93,2009:0.16,2010:0.18,2011:0.10,2012:0.14,2013:0.11,2014:0.09,2015:0.13,
     2016:0.40,2017:1.00,2018:1.83,2019:2.16,2020:0.38,2021:0.08,2022:1.68,2023:5.02,2024:5.14,2025:4.2,2026:3.8}
def fin_rate(idx,mode):
    if mode=='today': return pd.Series(0.126*365/4200,index=idx)          # today's broker swap as % of price ~1.1%/yr
    if mode=='ffr':   return pd.Series([FFR[y]/100+0.015 for y in idx.year],index=idx)  # rate + 1.5% markup
    if mode=='none':  return pd.Series(0.0,index=idx)
def run(d,pos,cost_side=0.0005,fin='today',exe='close'):
    """pos: desired exposure (x equity) decided at the close of each day. Returns daily strategy return series."""
    c=d.close; o=d.open
    pos=pos.reindex(d.index).fillna(0)
    days=d.index.to_series().diff().dt.days.fillna(1).clip(upper=4)   # calendar days financed (weekends)
    fr=fin_rate(d.index,fin)*days/365
    if exe=='close':
        held=pos.shift(1).fillna(0); ret=held*c.pct_change().fillna(0)
    else:  # trade at next day's open
        p0=pos.shift(2).fillna(0); p1=pos.shift(1).fillna(0)
        ret=p0*(o/c.shift(1)-1).fillna(0)+p1*(c/o-1)
        held=p1
    turn=pos.diff().abs().fillna(pos.abs()).shift(1).fillna(0)
    ret=ret-turn*cost_side-held.abs()*fr
    return ret
def stats(r,pos=None,name=''):
    r=r.dropna(); eq=(1+r).cumprod(); yrs=len(r)/252
    cagr=eq.iloc[-1]**(1/yrs)-1; vol=r.std()*np.sqrt(252); sh=r.mean()*252/vol if vol>0 else np.nan
    dd=(eq/eq.cummax()-1).min(); yr=(1+r).groupby(r.index.year).prod()-1
    out=dict(name=name,cagr=round(cagr*100,1),vol=round(vol*100,1),sharpe=round(sh,2),maxdd=round(dd*100,1),
             calmar=round(cagr/-dd,2),lose_yrs=f"{(yr<0).sum()}/{len(yr)}",worst_yr=round(yr.min()*100,1))
    if pos is not None:
        p=pos.reindex(r.index).fillna(0); out['in_mkt%']=round((p>0).mean()*100); out['switches/yr']=round(((p>0).astype(int).diff().abs().sum())/yrs,1)
    return out
def volest(c,n=20): return np.log(c).diff().rolling(n).std()*np.sqrt(252)
def ma_rule(c,n=200): return (c>c.rolling(n).mean()).astype(float).where(c.rolling(n).mean().notna(),0)
def volsize(c,tgt=0.15,cap=1.5,n=20): return (tgt/volest(c,n)).clip(upper=cap).fillna(0)
