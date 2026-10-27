"""Long/short decomposition and drift-adjusted TRAIN edge for the scan1 leaders."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from sigs import *
from mlib import Harness, spread_series
H = Harness(); m1 = H.m1; spr = spread_series(m1, 'base'); o, h, l, c = arrs(m1)
b5, p5 = htf_bars(m1, 5); O5, H5, L5, C5 = arrs(b5)
tr = m1.index < SPLIT
cands = {
 'brk_M5_60': place(m1, p5, breakout(O5, H5, L5, C5, 60)),
 'ob_M1_k8_W30': structure(o, h, l, c, 8, 30, kind=2),
 'ob_M1_k5_W30': structure(o, h, l, c, 5, 30, kind=2),
 'rn10_reject_inv_e0.5': -round_level(o, h, l, c, 10, 'reject', 0.5),
 'rn10_reject_inv_e0.2': -round_level(o, h, l, c, 10, 'reject', 0.2),
 'sweep_M1_5_d.3_col_cf.3': sweep(o, h, l, c, 5, 0.3, True, 0.3),
 'fvgret_M1_g1_W15': fvg_retrace(o, h, l, c, 1.0, 15, 0),
 'fvgret_M1_g2_W15': fvg_retrace(o, h, l, c, 2.0, 15, 0),
 'fvgret_M5_g.2_W5': place(m1, p5, fvg_retrace(O5, H5, L5, C5, 0.44, 5, 0)),
 'choch_M5_k3_inv': -place(m1, p5, structure(O5, H5, L5, C5, 3, kind=3)),
 'bos_M5_k2_inv': -place(m1, p5, structure(O5, H5, L5, C5, 2, kind=0)),
 'fvgimm_M5_g2_inv': -place(m1, p5, fvg_imm(O5, H5, L5, C5, 4.4)),
}
rows = []
for k in (1, 3, 5, 10, 20):
    f = np.full(len(c), np.nan); f[:-k] = c[k:] - c[:-k]
    drift = np.nanmean(f[tr])
    for name, s in cands.items():
        s = s.astype(float)
        for side in (1, -1):
            msk = (s == side) & tr
            a = (f * s)[msk]; a = a[~np.isnan(a)]
            rows.append(dict(name=name, side=side, k=k, n_day=msk.sum() / 47, mv=a.mean(), adj=a.mean() - side * drift, spr=spr[msk].mean()))
d = pd.DataFrame(rows)
print('always-long TRAIN drift per k:', {k: round(np.nanmean((np.r_[c[k:], [np.nan]*k] - c)[tr]), 3) for k in (1, 3, 5, 10, 20)})
pd.set_option('display.width', 250)
p = d.pivot_table(index=['name', 'side'], columns='k', values=['mv', 'adj']).round(3)
p['n_day'] = d.groupby(['name', 'side']).n_day.first().round(1); p['spr'] = d.groupby(['name', 'side']).spr.first().round(3)
print(p.to_string())
