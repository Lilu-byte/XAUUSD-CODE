import numpy as np, pandas as pd
exec(open('paths.py').read().split("print('patterns with a full path:'")[0].replace("rows.append(dict(tf=tf, kind=kd, grp=GROUP[kd], date=t[conf], L=L, y=y, base=np.array(base), tgt_frac=D))",
 "rows.append(dict(tf=tf, kind=kd, grp=GROUP[kd], date=t[conf], L=L, y=y, base=np.array(base), dr=dr, trend=int(np.sign(e50[conf]-e200[conf])), mom=int(np.sign(c[conf]-c[max(0,conf-3*L)])), vol=a[conf]/np.median(a[max(0,conf-500):conf+1])))").replace(
 "    t = pd.to_datetime(", "    e50 = pd.Series(c).ewm(span=50).mean().values; e200 = pd.Series(c).ewm(span=200).mean().values\n    t = pd.to_datetime("))
R = pd.DataFrame([dict(tf=r['tf'], kind=r['kind'], date=r['date'], end=r['y'][-1], mid=r['y'][8], way=r['y'][-1] > 0,
                       agree=r['dr'] == r['trend'], mom=r['dr'] == r['mom'], hv=r['vol'] > 1.2, bway=np.mean(r['base'][:, -1] > 0)) for r in rows])
R['test'] = R.date >= pd.Timestamp('2024-01-01')
for col in ['agree', 'mom', 'hv']:
    print(col); print(R.groupby(['test', col]).agg(n=('way', 'size'), way=('way', 'mean'), rand=('bway', 'mean'), med_end=('end', 'median')).round(3))
print(R.groupby(['test', 'tf']).agg(n=('way', 'size'), way=('way', 'mean'), rand=('bway', 'mean')).round(3))
for k in [9, 10, 15, 16, 17, 18, 6, 7]:
    print(KINDS[k], R[R.kind == k].groupby('test').agg(n=('way', 'size'), way=('way', 'mean'), rand=('bway', 'mean')).round(2).to_dict('index'))
