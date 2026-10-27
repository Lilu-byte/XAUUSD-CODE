"""TRAIN-only: 'pullback against the trend reference' fade. A big short-term move AGAINST the prevailing side
(price above trend ref + sharp drop -> buy; below + sharp rally -> sell). Thresholds normalised by atr240."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from scan_lib import *
H = Harness(); m = H.m1; f = build(m); S = Scanner(m, f)
sg = lambda x: np.sign(np.nan_to_num(x))
c = m.close
trend = {
    'vwap': sg(f.vw_d.values),
    'ema60': sg((c - ema(c, 60)).values),
    'ema240': sg((c - ema(c, 240)).values),
    'r60': sg((c - c.shift(60)).values),
    'vwap1atr': np.where(np.abs(f.vw_d.values) > f.atr240.values, sg(f.vw_d.values), 0),
}
a240 = f.atr240.values
for mv in ('r1', 'r2', 'r3', 'r5'):
    r = f[mv].values
    for th in (1.5, 2, 2.5, 3, 4):
        fade = np.where(np.abs(r) > th * a240, -sg(r), 0)
        for tn, ts in trend.items():
            for vn, vf in (('all', np.ones(len(m), bool)), ('vreg>1.2', f.vreg.values > 1.2)):
                S.add(f'{mv}>{th}a|{tn}|{vn}', np.where((ts == fade) & vf, fade, 0))
        S.add(f'{mv}>{th}a|none|all', fade)
t = S.table()
for k in KS:
    t[f'n{k}'] = t[f'm{k}T'] - t.sprT; t[f'n{k}A'] = t[f'm{k}A'] - t.sprA; t[f'n{k}B'] = t[f'm{k}B'] - t.sprB
t.to_csv('scan3_train.csv')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
cols = ['nT', 'sprT', 'n1', 'n2', 'n3', 'n5', 'n10', 'n15', 'n20', 'n5A', 'n5B', 'n10A', 'n10B']
print(t[cols].sort_values('n5', ascending=False).head(40).round(3).to_string())
print('\nby trend ref (mean n5 over all move/threshold, vol=all):')
for tn in list(trend) + ['none']:
    s = t[[i.split('|')[1] == tn and i.endswith('|all') for i in t.index]]
    print(f'  {tn:9s} mean n3 {s.n3.mean():.3f} n5 {s.n5.mean():.3f} n10 {s.n10.mean():.3f}  frac n5A>0&n5B>0 {((s.n5A > 0) & (s.n5B > 0)).mean():.2f}  avg sig/day {s.nT.mean():.1f}')
print('signals tested', len(t))
