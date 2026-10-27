"""TRAIN only: is the VWAP-pullback edge just VWAP-side trend following? + day-clustered t-stats."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from scan_lib import *
H = Harness(); m = H.m1; f = build(m)
sg = lambda x: np.sign(np.nan_to_num(x))
ok = valid_mask(m, f); tr = (m.index < SPLIT)
F = fwd(m, (1, 3, 5, 10, 20)); spr = spread_series(m, 'base'); day = H.day
def stats(name, d):
    d = np.where(ok & tr, d, 0); s = d != 0
    out = [f'{name:28s} n/day {s.sum()/47:6.1f}']
    for k in (1, 3, 5, 10, 20):
        x = F[k] * d - spr * np.abs(d); x = np.where(s, x, np.nan)
        ds = pd.Series(x).groupby(day).sum(min_count=1).dropna()   # daily sum of net move
        cnt = pd.Series(s.astype(float)).groupby(day).sum(); cnt = cnt[ds.index]
        # clustered t of the per-signal mean: daily sums, ratio estimator
        mu = np.nansum(x) / s.sum(); res = ds - mu * cnt
        se = np.sqrt((res ** 2).sum()) / s.sum()
        out.append(f'net{k} {mu:6.3f} (t {mu/se:4.1f})')
    print('  '.join(out))
vs = sg(f.vw_d.values); a = f.atr240.values
stats('vwap side follow (all bars)', vs)
stats('vwap side, |d|>1atr', np.where(np.abs(f.vw_d.values) > a, vs, 0))
stats('vwap side, |d|>3atr', np.where(np.abs(f.vw_d.values) > 3 * a, vs, 0))
for k, th in (('r3', 2), ('r3', 2.5), ('r3', 3), ('r2', 2.5), ('r1', 1.5), ('r5', 2.5)):
    r = f[k].values; fade = np.where(np.abs(r) > th * a, -sg(r), 0)
    stats(f'{k}>{th}a fade | vwap', np.where(vs == fade, fade, 0))
    stats(f'{k}>{th}a fade | anti-vwap', np.where(vs == -fade, fade, 0))
    stats(f'{k}>{th}a follow | vwap(=with trend)', np.where(vs == -fade, -fade, 0))
