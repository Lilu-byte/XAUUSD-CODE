"""The full signal library of this family as FOLLOW-direction arrays (fade = negative)."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from sigs import *


def library(m, f):
    L = {}
    b = sg(f.body.values); a240 = f.atr240.values; hr = m.index.hour.values; vs = sg(f.vw_d.values)
    for k in (1, 2, 3, 5):
        r = f[f'r{k}'].values
        L[f'r{k}_any'] = sg(r)
        for th in (0.5, 1, 2, 3, 4, 6): L[f'r{k}>{th}$'] = np.where(np.abs(r) > th, sg(r), 0)
        for th in (0.5, 1, 1.5, 2, 2.5, 3, 4):
            L[f'r{k}>{th}a'] = np.where(np.abs(r) > th * a240, sg(r), 0)
            L[f'r{k}>{th}a|vw'] = np.where((np.abs(r) > th * a240) & (vs == sg(r)), sg(r), 0)    # move away from vwap side? (with trend)
            L[f'r{k}>{th}a|avw'] = np.where((np.abs(r) > th * a240) & (vs == -sg(r)), sg(r), 0)  # move against vwap side (pullback)
    L['body_any'] = b
    st = f.streak.values
    for n in (2, 3, 4, 5, 6, 7):
        L[f'streak=={n}'] = np.where(np.abs(st) == n, sg(st), 0); L[f'streak>={n}'] = np.where(np.abs(st) >= n, sg(st), 0)
    for n in (2, 3, 7):
        x = f[f'rsi{n}'].values
        for lo in (2, 5, 10, 20, 30): L[f'rsi{n}_ext{lo}'] = np.where(x > 100 - lo, 1, np.where(x < lo, -1, 0))
    for n in (10, 20, 30, 60):
        z = f[f'z{n}'].values
        for th in (1, 1.5, 2, 2.5, 3): L[f'z{n}>{th}'] = np.where(z > th, 1, np.where(z < -th, -1, 0))
        bu = f[f'bbu{n}'].values > 0; bl = f[f'bbl{n}'].values > 0
        L[f'bb{n}_touch'] = np.where(bu & ~bl, 1, np.where(bl & ~bu, -1, 0))
        L[f'bb{n}_reject'] = np.where(bu & (z < 2), 1, np.where(bl & (z > -2), -1, 0))
    vd = f.vw_d.values; vda = f.vw_d.values / a240
    for th in (0, 2, 4, 6, 10, 15): L[f'vwap>{th}$'] = np.where(np.abs(vd) > th, sg(vd), 0)
    for th in (1, 2, 4, 6, 10): L[f'vwap>{th}a'] = np.where(np.abs(vda) > th, sg(vd), 0)
    vr = f.vrel.values
    for th in (1.5, 2, 3, 4, 6):
        L[f'vspike>{th}'] = np.where(vr > th, b, 0); L[f'vquiet<{1/th:.2f}'] = np.where(vr < 1 / th, b, 0)
    rx = f.rexp.values
    for th in (1.5, 2, 2.5, 3, 4):
        L[f'rexp>{th}'] = np.where(rx > th, b, 0)
        L[f'rexp>{th}_sc'] = np.where((rx > th) & ((f.cloc.values > .8) | (f.cloc.values < .2)), b, 0)
    L['ib_break_mother'] = np.where(f.ib_up.values, 1, np.where(f.ib_dn.values, -1, 0))
    L['ib_break_inside'] = np.where(f.ib_up2.values, 1, np.where(f.ib_dn2.values, -1, 0))
    for th in (0.1, 0.2, 0.3): L[f'cloc_ext{th}'] = np.where(f.cloc.values > 1 - th, 1, np.where(f.cloc.values < th, -1, 0))
    # vol regime splits of the simplest momentum signal
    for q in (.25, .5, .75):
        L[f'r1_any|atrq<{q}'] = np.where(f.atrq.values < q, sg(f.r1.values), 0)
        L[f'r1_any|atrq>{q}'] = np.where(f.atrq.values > q, sg(f.r1.values), 0)
    ok = valid_mask(m, f)
    return {k: np.where(ok, np.nan_to_num(np.asarray(v, float)), 0) for k, v in L.items()}
