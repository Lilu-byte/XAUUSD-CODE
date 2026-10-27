"""TRAIN-only: refine the fade-the-big-move effect found in scan1 with filters (reversal bar, vol regime,
session, VWAP side, first-of-cluster). Direction here is the FADE direction (positive move = fade earns)."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from scan_lib import *
H = Harness(); m = H.m1; f = build(m); S = Scanner(m, f)
sg = lambda x: np.sign(np.nan_to_num(x))
b = sg(f.body.values); hr = m.index.hour.values
bases = {
    'r3>6$': np.where(np.abs(f.r3) > 6, -sg(f.r3), 0),
    'r3>4$': np.where(np.abs(f.r3) > 4, -sg(f.r3), 0),
    'r2>4$': np.where(np.abs(f.r2) > 4, -sg(f.r2), 0),
    'r1>3$': np.where(np.abs(f.r1) > 3, -sg(f.r1), 0),
    'r5>6$': np.where(np.abs(f.r5) > 6, -sg(f.r5), 0),
    'r3>2atr': np.where(np.abs(f.r3 / f.atr20) > 2, -sg(f.r3), 0),
    'rexp>2.5': np.where(f.rexp > 2.5, -b, 0),
    'z20>2.5': np.where(f.z20 > 2.5, -1, np.where(f.z20 < -2.5, 1, 0)),
    'z60>2.5': np.where(f.z60 > 2.5, -1, np.where(f.z60 < -2.5, 1, 0)),
    'rsi3_ext5': np.where(f.rsi3 > 95, -1, np.where(f.rsi3 < 5, 1, 0)),
}
atr240 = f.atr240.values
filters = {
    'all': np.ones(len(m), bool),
    'lastbar_turned': None,      # filled per base: bar i body already in the fade direction
    'lastbar_running': None,     # bar i body still in the move direction
    'atrq>.5': f.atrq.values > .5, 'atrq<.5': f.atrq.values <= .5, 'atrq>.8': f.atrq.values > .8,
    'vreg>1.3': f.vreg.values > 1.3, 'vreg<1': f.vreg.values < 1,
    'h01-08': (hr >= 1) & (hr < 9), 'h09-14': (hr >= 9) & (hr < 15), 'h15-18': (hr >= 15) & (hr < 19), 'h19-23': hr >= 19,
    'away_vwap': None, 'to_vwap': None,
    'first_in_10': None,
    'spr<=.15': m.spread_usd.values <= .15,
    'atr240>1.5': atr240 > 1.5, 'atr240<1.5': atr240 <= 1.5,
}
vside = sg(f.vw_d.values)   # +1 above vwap
for bn, d in bases.items():
    d = np.nan_to_num(d.astype(float))
    for fn, flt in filters.items():
        if fn == 'lastbar_turned': flt = (b == d)
        elif fn == 'lastbar_running': flt = (b == -d)
        elif fn == 'away_vwap': flt = (vside == -d)      # move pushed price further from vwap; fade = back toward
        elif fn == 'to_vwap': flt = (vside == d)
        elif fn == 'first_in_10':
            prev = pd.Series(np.abs(d)).shift(1).rolling(10, min_periods=1).max().fillna(0).values
            flt = prev == 0
        S.add(f'{bn}|{fn}', np.where(flt, d, 0))
t = S.table()
t.to_csv('scan2_train.csv')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
# here direction is fade, so positive m = good
t['net3'] = t.m3T - t.sprT; t['net5'] = t.m5T - t.sprT; t['net1'] = t.m1T - t.sprT; t['net2'] = t.m2T - t.sprT
t['net3A'] = t.m3A - t.sprA; t['net3B'] = t.m3B - t.sprB; t['net5A'] = t.m5A - t.sprA; t['net5B'] = t.m5B - t.sprB
cols = ['nT', 'sprT', 'net1', 'net2', 'net3', 'net5', 'net3A', 'net3B', 'net5A', 'net5B', 't3']
for bn in bases:
    print(t.loc[[i for i in t.index if i.startswith(bn + '|')], cols].round(3).to_string()); print()
print('signals tested', len(t))
