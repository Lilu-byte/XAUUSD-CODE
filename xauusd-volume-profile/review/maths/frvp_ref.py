# Independent reference for the profile maths of FixedRangeVolumeProfile.mq5.
# - Prices are converted to integer cents; the grid (base, rows, row bounds) is computed with exact
#   integer / rational arithmetic, not with the code's floating-point formulas.
# - Each candle's volume is first spread over a 1-cent grid (a density per cent cell, built with a
#   difference array in long double), then the cent cells are aggregated into the rows. A cent cell cut
#   by a row bound (row-count mode) is split exactly in proportion.
# - "levels" model (sensitivity only, not what the code claims to do): the volume is spread over the
#   candle's discrete price levels L, L+1c, ..., H (inclusive) instead of the continuous range [L, H].
# - POC and value area are computed with separate code; the value area is also checked against the
#   narrowest contiguous window that contains the POC and holds the target share.
import numpy as np

LD = np.longdouble


def grid(Hc, Lc, rows_in=60, rowsize=0.0):
    loc = int(Lc.min()); hic = int(Hc.max())
    if hic == loc: hic = loc + 1                       # same rule as hi = lo + _Point
    if rowsize > 0:
        sc = int(round(rowsize * 100))
        assert abs(rowsize * 100 - sc) < 1e-9 and sc >= 1, "reference supports row sizes in whole cents"
        base = (loc // sc) * sc
        rows = -((base - hic) // sc)                   # ceil((hic-base)/sc)
        rows = max(rows, 1)
        if rows <= 2000:
            return dict(mode='size', D=1, rows=rows, num=[base + k * sc for k in range(rows + 1)],
                        base_c=base, sc=sc, loc=loc, hic=hic)
        rows_in = 2000                                  # capped: falls back to 2000 equal rows over lo..hi
    W = hic - loc
    return dict(mode='rows', D=rows_in, rows=rows_in, num=[loc * rows_in + k * W for k in range(rows_in + 1)],
                W=W, loc=loc, hic=hic)


def row_of_point(g, pc):
    if g['mode'] == 'size':
        k = (pc - g['base_c']) // g['sc']
    else:
        k = ((pc - g['loc']) * g['rows']) // g['W']
    return np.clip(k, 0, g['rows'] - 1)


def spread(Hc, Lc, v, up, g, model='continuous'):
    R = g['rows']; off = g['loc']; ncell = g['hic'] - off
    out = {}
    for side, mask in (('up', up), ('dn', ~up)):
        m = mask & (v > 0)
        H = Hc[m]; L = Lc[m]; V = v[m].astype(LD)
        rowv = np.zeros(R, dtype=LD)
        if model == 'continuous':
            rng = H > L
            d = np.zeros(ncell + 1, dtype=LD)
            dens_add = V[rng] / (H[rng] - L[rng]).astype(LD)
            np.add.at(d, L[rng] - off, dens_add)
            np.add.at(d, H[rng] - off, -dens_add)
            dens = np.cumsum(d)[:ncell]                # volume per cent cell [off+j, off+j+1)
            Cc = np.concatenate([[LD(0)], np.cumsum(dens)])
            D = g['D']

            def C(num):                                 # volume below price num/D cents
                rel = num - off * D
                if rel <= 0: return LD(0)
                j, r = divmod(rel, D)
                if j >= ncell: return Cc[ncell]
                return Cc[j] + LD(r) / LD(D) * dens[j]
            cb = [C(x) for x in g['num']]
            cb[0] = LD(0); cb[-1] = Cc[ncell]          # bottom/top rows hold everything below/above
            rowv += np.array([cb[k + 1] - cb[k] for k in range(R)], dtype=LD)
            pts = ~rng                                  # high == low: all of it at that price
            np.add.at(rowv, row_of_point(g, L[pts]), V[pts])
        else:                                           # discrete price levels, inclusive
            d = np.zeros(ncell + 2, dtype=LD)
            per = V / (H - L + 1).astype(LD)
            np.add.at(d, L - off, per)
            np.add.at(d, H - off + 1, -per)
            lev = np.cumsum(d)[:ncell + 1]
            ks = row_of_point(g, np.arange(off, off + ncell + 1))
            np.add.at(rowv, ks, lev)
        out[side] = rowv
    return out['up'].astype(float), out['dn'].astype(float)


def poc_va(tot, pct=70.0):
    R = len(tot); s = float(np.sum(tot)); mx = float(tot.max())
    mid = (R - 1) / 2.0
    cand = np.nonzero(tot >= mx * (1 - 1e-12))[0]
    poc = int(min(cand, key=lambda k: (abs(k - mid), k)))
    target = s * pct / 100.0
    P = np.concatenate([[0.0], np.cumsum(tot)])
    lo = hi = poc
    while P[hi + 1] - P[lo] < target - s * 1e-12 and not (lo == 0 and hi == R - 1):
        a = tot[hi + 1] if hi + 1 < R else -1.0
        b = tot[lo - 1] if lo > 0 else -1.0
        if a >= b: hi += 1
        else: lo -= 1
    # narrowest contiguous window containing the POC with >= target
    best = None
    for l in range(0, poc + 1):
        need = P[l] + target - s * 1e-12
        h = int(np.searchsorted(P, need, side='left')) - 1   # smallest h with P[h+1] >= need
        h = max(h, poc)
        if h >= R: continue
        w = h - l + 1
        vol = P[h + 1] - P[l]
        if best is None or w < best[0] or (w == best[0] and vol > best[3]):
            best = (w, l, h, vol)
    # fewest rows of any kind (not contiguous) reaching the target: a lower bound
    srt = np.sort(tot)[::-1]
    kmin = int(np.searchsorted(np.cumsum(srt), target - s * 1e-12, side='left')) + 1
    return dict(poc=poc, vaLo=lo, vaHi=hi, share=(P[hi + 1] - P[lo]) / s, sum=s,
                opt_w=best[0], opt_lo=best[1], opt_hi=best[2], opt_share=best[3] / s, kmin=kmin)


def prices(g, poc, vaLo, vaHi):
    if g['mode'] == 'size':
        b, sc = g['base_c'], g['sc']
        return ((b + (poc + 0.5) * sc) / 100.0, (b + (vaHi + 1) * sc) / 100.0, (b + vaLo * sc) / 100.0)
    loc, W, R = g['loc'], g['W'], g['rows']
    f = lambda x: (loc + x * W / R) / 100.0
    return (f(poc + 0.5), f(vaHi + 1), f(vaLo))


def profile(df, rows=60, rowsize=0.0, pct=70.0, model='continuous'):
    Hc = np.round(df['high'].values * 100).astype(np.int64)
    Lc = np.round(df['low'].values * 100).astype(np.int64)
    v = df['tick_volume'].values.astype(np.int64)
    up = df['close'].values >= df['open'].values
    g = grid(Hc, Lc, rows, rowsize)
    u, d = spread(Hc, Lc, v, up, g, model)
    tot = u + d
    r = poc_va(tot, pct)
    pocPx, vah, val = prices(g, r['poc'], r['vaLo'], r['vaHi'])
    r.update(g=g, rows=g['rows'], up=u, dn=d, tot=tot, pocPx=pocPx, vah=vah, val=val)
    return r
