import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from scan_lib import *
H = Harness(); m = H.m1; f = build(m)
tr = m.index < SPLIT
print('price path train: ', m.close[tr].iloc[[0, -1]].values, ' per-bar drift', (m.close[tr].iloc[-1]-m.close[tr].iloc[0])/tr.sum())
print('daily close (train) every 5 days:', m.close[tr].resample('D').last().dropna().iloc[::5].round(0).values)
print('atr240 train quantiles', np.nanquantile(f.atr240[tr], [.1,.5,.9]).round(2))
sg = lambda x: np.sign(np.nan_to_num(x))
ok = valid_mask(m, f)
d = np.where(np.abs(f.r3) > 6, -sg(f.r3), 0); vside = sg(f.vw_d.values)
sel = (d != 0) & (vside == d) & tr & ok
F = fwd(m, (1,3,5,10,15,20))
for side in (1, -1):
    s = sel & (d == side)
    print('side', side, 'n/day', s.sum()/47, {k: round(np.nanmean(F[k][s]*side), 3) for k in F})
