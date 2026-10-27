import sys; sys.path.insert(0,'../cp')
import detect as D, detect_ref as R, pandas as pd
df=D.load('H1').iloc[50000:53000].reset_index(drop=True)
D.load=lambda tf: df
_,_,orig=D.detect_tf('H1')
R.dedupe=lambda x:x
ref,_=R.detect(df.open.values,df.high.values,df.low.values,df.close.values,forming=False)
so=set((r['kind'],r['s'],r['e']) for r in orig); sr=set((R.KINDS[r['kind']],r['s'],r['e']) for r in ref)
print(len(so),len(sr),'only orig',sorted(so-sr)[:10],'only ref',sorted(sr-so)[:10])
