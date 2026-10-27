import sys
sys.path.insert(0,'/home/claude/bt')
from pa_backtest import *
h1=pd.read_pickle('mt5_h1.pkl'); h4=pd.read_pickle('mt5_h4.pkl'); d1=pd.read_pickle('mt5_d1.pkl')
for name,b,k in (("D1",d1,2),("H4",h4,3)):
    S=structure(b,k)
    ev=np.nonzero(S['event'])[0]
    print(f"\n### {name}: trend now {S['trend'][-1]}, last swing high {S['last_sh'][-1]}, last swing low {S['last_sl'][-1]}")
    print(" last 6 structure events:")
    for j in ev[-6:]:
        print("  ",b.index[j], "BULL break" if S['event'][j]==1 else "BEAR break", "close",b.c.iloc[j], "broke",S['broken'][j])
    print(" last 8 swing highs:",[(str(b.index[p])[:16],round(v,2)) for p,v in S['swings_h'][-8:]])
    print(" last 8 swing lows:",[(str(b.index[p])[:16],round(v,2)) for p,v in S['swings_l'][-8:]])
    avg=(b.h-b.l).rolling(20).mean()
    t=b.tail(12 if name=="D1" else 18).copy()
    t['rng']=t.h-t.l; t['body']=(t.c-t.o); t['closepos']=((t.c-t.l)/t.rng).round(2); t['rng/avg']=(t.rng/avg.shift(1).reindex(t.index)).round(2)
    print(t[['o','h','l','c','body','rng','closepos','rng/avg']].round(2).to_string())
print("\nD1 range: 20d high/low",d1.h.tail(20).max(),d1.l.tail(20).min()," 60d",d1.h.tail(60).max(),d1.l.tail(60).min(), " ATH", d1.h.max(), d1.h.idxmax())
s=find_setups(h4,d1,k_h4=3,k_d1=2,tol=1.0,max_range_pos=0.5); print("\nRecent tuned-rule H4 setups:\n",s.tail(4).to_string())
s2=find_setups(h4,d1,k_h4=2,k_d1=2,tol=0.5,max_range_pos=0.5); print("\nRecent as-written setups:\n",s2.tail(4).to_string())
print("\nH1 last 12:\n",h1.tail(12)[['o','h','l','c']].to_string())
