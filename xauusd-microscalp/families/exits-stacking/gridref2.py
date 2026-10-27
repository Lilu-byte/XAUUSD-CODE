"""Independent pure-Python re-implementation of the grid basket rules (OHLC in-bar path, deterministic) written from
the gridsim2 docstring, run on 4 TRAIN days and compared day by day with gridsim2.run_grid(path='OHLC').
The reference walks each straight segment in $0.002 increments (a crude 'tick' walk) instead of solving for levels."""
from sigs2 import *
from gridsim2 import run_grid
import math


def ref(H, sig, step, maxlev, btp, bsl, tmax, idx):
    o, h, l, c, spr, tod, last = H.o, H.h, H.l, H.c, H._spr['base'], H.tod, H.last
    pnl = {}; pos = None   # pos: dict(d, entries list, t0)
    def flt(x, a):
        if pos['d'] == 1: return sum(x - e for e in pos['e'])
        return sum(e - (x + a) for e in pos['e'])
    def bclose(x, a, i):
        nonlocal pos
        v = flt(x, a); dd = H.day[pos['t0']]; pnl[dd] = pnl.get(dd, 0.0) + v; pos = None
    for i in idx:
        a = spr[i]
        if pos is not None:
            # gap: previous close -> open
            x = o[i]; p0 = c[i - 1]
            if pos['d'] == 1:
                if flt(x, a) >= btp - 1e-9: bclose(x, a, i)
                elif bsl > 0 and flt(x, a) <= -bsl + 1e-9: bclose(x, a, i)
                elif x + a <= pos['e'][-1] - step + 1e-9 and len(pos['e']) < maxlev: pos['e'].append(x + a)
            else:
                if flt(x, a) >= btp - 1e-9: bclose(x, a, i)
                elif bsl > 0 and flt(x, a) <= -bsl + 1e-9: bclose(x, a, i)
                elif x >= pos['e'][-1] + step - 1e-9 and len(pos['e']) < maxlev: pos['e'].append(x)
            verts = [o[i], l[i], h[i], c[i]] if c[i] > o[i] else [o[i], h[i], l[i], c[i]]
            for v in range(3):
                if pos is None: break
                p, q = verts[v], verts[v + 1]
                nst = max(1, int(round(abs(q - p) / 0.002)))
                for k in range(1, nst + 1):
                    if pos is None: break
                    x = p + (q - p) * k / nst
                    if pos['d'] == 1:
                        if flt(x, a) >= btp - 1e-9: bclose(x, a, i); break
                        if bsl > 0 and flt(x, a) <= -bsl + 1e-9: bclose(x, a, i); break
                        if x + a <= pos['e'][-1] - step + 1e-9 and len(pos['e']) < maxlev: pos['e'].append(x + a)
                    else:
                        if flt(x, a) >= btp - 1e-9: bclose(x, a, i); break
                        if bsl > 0 and flt(x, a) <= -bsl + 1e-9: bclose(x, a, i); break
                        if x >= pos['e'][-1] + step - 1e-9 and len(pos['e']) < maxlev: pos['e'].append(x)
            if pos is not None and ((tmax > 0 and i - pos['t0'] >= tmax) or tod[i] >= 22 * 60 + 58 or last[i]):
                bclose(c[i], a, i)
        if pos is None and sig[i] != 0 and 65 <= tod[i] <= 22 * 60 + 29 and not last[i]:
            pos = dict(d=int(sig[i]), e=[c[i] + a if sig[i] == 1 else c[i]], t0=i)
    return pnl


m1, H = train_harness(); S = build(m1); tr = m1.index < SPLIT
days = [10, 27, 35, 44]
idx = np.where(np.isin(H.day, days))[0]
for s, step, lev, btp, bsl, tm in [('MR', 2.0, 50, 0.3, 0, 0), ('CF', 1.0, 10, 0.3, 0, 0), ('AB', 3.0, 20, 0.5, 50, 30), ('HTF', 0.5, 5, 1.0, 20, 0)]:
    sig = np.where(np.isin(H.day, days), S[s][tr], 0)
    d, b, e, lv = run_grid(H, sig, step, lev, btp, bsl, tmax=tm, path='OHLC')
    r = ref(H, sig, step, lev, btp, bsl, tm, idx)
    diffs = [abs(d.pnl.iloc[k] - r.get(k, 0.0)) for k in days]
    print(f'{s} {step}/{lev}/{btp}/{bsl}/{tm}: gridsim2 days {[round(d.pnl.iloc[k], 2) for k in days]}')
    print(f'{" " * len(s)}  reference           {[round(r.get(k, 0.0), 2) for k in days]}  max abs diff {max(diffs):.3f}')
