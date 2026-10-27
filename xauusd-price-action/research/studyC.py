import numpy as np, pandas as pd
from feats import load
cal=pd.read_csv('/home/claude/data/mt5/x/XAU_Export/USD_calendar.csv')
cal['t']=pd.to_datetime(cal.time,format='%Y.%m.%d %H:%M')
skip=('Auction','Crude','Speech','Press','Testimony','Decision','n.s.a')
cal=cal[(cal.importance==3)&cal.actual.notna()&cal.forecast.notna()&~cal.event.str.contains('|'.join(skip))].copy()
neg=('Unemployment Rate','Initial Jobless Claims')
cal['pol']=np.where(cal.event.isin(neg),-1,1)
cal['s']=cal.actual-cal.forecast
# standardise each event's surprise by the std of its own PAST surprises (expanding, no lookahead)
cal=cal.sort_values('t')
cal['sd']=cal.groupby('event').s.transform(lambda x: x.abs().expanding().mean().shift(1))
cal['z']=cal.pol*cal.s/cal.sd
cal=cal[cal.sd.notna()&(cal.sd>0)]
ev=cal.groupby('t').agg(z=('z','sum'),names=('event',lambda s:'; '.join(s))).reset_index()
m15=load('XAUUSD_M15'); m5=load('XAUUSD_M5')
def outcome(bars, step, ev):
    idx=bars.index; out=[]
    for e in ev.itertuples():
        i=idx.searchsorted(e.t)
        if i>=len(idx) or idx[i]!=e.t or i+48>=len(idx): out.append(None); continue
        o=bars.o.iloc[i]; c0=bars.c.iloc[i]
        k1=int(60/step); k4=int(240/step)
        out.append(dict(r0=c0-o, c1h=bars.c.iloc[i+k1]-c0, c4h=bars.c.iloc[i+k4]-c0, eod=bars.c.iloc[min(i+int(360/step),len(idx)-1)]-c0))
    return pd.DataFrame([x if x else {} for x in out],index=ev.index)
for name,bars,step in (("M15 (2022-10..2026-10)",m15,15),("M5 (2025-05..2026-10)",m5,5)):
    o=outcome(bars,step,ev); E=pd.concat([ev,o],axis=1).dropna(subset=['r0'])
    E=E[E.z!=0]
    pred=-np.sign(E.z)  # USD-positive surprise -> gold down
    print(f"\n== {name}: release times with a surprise n={len(E)}")
    for thr in (0,0.5,1.0,1.5):
        s=E.z.abs()>thr
        x=E[s]; p=pred[s]
        print(f" |z|>{thr}: n={s.sum():3d} | first {step}m bar moves opposite to USD surprise {100*(np.sign(x.r0)==p).mean():.0f}%"
              f" | continuation after that bar: +1h {100*(np.sign(x.c1h)==p).mean():.0f}%, +4h {100*(np.sign(x.c4h)==p).mean():.0f}%"
              f" | follow first bar's direction +1h {100*(np.sign(x.c1h)==np.sign(x.r0)).mean():.0f}%")
    E.to_pickle(f"C_{step}.pkl")
