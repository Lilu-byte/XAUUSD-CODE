"""Reference for GoldPatterns.mq5: the app's detector (cp/detect.py) rewritten in the same shape as the MQL5 code,
plus 'forming' patterns (structure done, breakout not yet) and a causal de-duplication (earliest confirmed wins).
Usage: python3 detect_ref.py data.csv first_bar last_bar   -> prints one line per pattern, sorted."""
import sys
import numpy as np

KINDS = ['double_top', 'double_bottom', 'triple_top', 'triple_bottom', 'head_shoulders', 'inv_head_shoulders',
         'asc_triangle', 'desc_triangle', 'sym_triangle', 'rising_wedge', 'falling_wedge', 'rectangle', 'broadening',
         'channel_up', 'channel_down', 'bull_flag', 'bear_flag', 'bull_pennant', 'bear_pennant',
         'cup_handle', 'inv_cup_handle', 'rounding_bottom', 'rounding_top']
K = {k: i for i, k in enumerate(KINDS)}


def atr(h, l, c, n=14):
    out = np.empty(len(c))
    for i in range(len(c)):
        pc = c[i - 1] if i > 0 else c[0]
        tr = max(h[i] - l[i], abs(h[i] - pc), abs(l[i] - pc))
        out[i] = tr if i == 0 else out[i - 1] + (tr - out[i - 1]) / n
    return out


def zigzag(h, l, a, k):
    piv = []
    d = 0
    ei, ep = 0, h[0]
    li, lp = 0, l[0]
    for i in range(1, len(h)):
        if d >= 0:
            if h[i] > ep:
                ei, ep = i, h[i]
            if d == 0 and l[i] < lp:
                li, lp = i, l[i]
            if ep - l[i] >= k * a[i] and (d == 1 or ei < i):
                if d == 0 and li < ei:
                    piv.append((li, lp, -1, ei))
                piv.append((ei, ep, 1, i))
                d = -1
                ei, ep = i, l[i]
                continue
        if d <= 0:
            if d == 0:
                if h[i] - lp >= k * a[i] and li < i:
                    piv.append((li, lp, -1, i))
                    d = 1
                    ei, ep = i, h[i]
                continue
            if l[i] < ep:
                ei, ep = i, l[i]
            if h[i] - ep >= k * a[i]:
                piv.append((ei, ep, -1, i))
                d = 1
                ei, ep = i, h[i]
    return piv


def linfit(xs, ys):
    """least squares line; returns (slope, intercept)"""
    n = len(xs)
    if n == 2:
        m = (ys[1] - ys[0]) / (xs[1] - xs[0])
        return m, ys[0] - m * xs[0]
    sx = sum(xs); sy = sum(ys); sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
    den = n * sxx - sx * sx
    m = (n * sxy - sx * sy) / den
    return m, (sy - m * sx) / n


def first_close(c, start, end, m, b, side, margin, n):
    for i in range(start, min(end, n)):
        f = m * i + b
        if side == 1 and c[i] > f + margin:
            return i
        if side == -1 and c[i] < f - margin:
            return i
    return -1


def detect(o, h, l, c, scales=(1.5, 2.0, 3.0, 4.5), forming=True, warm=0):
    n = len(c)
    a = atr(h, l, c)
    out = []

    def add(kind, s, e, brk, dr, conf, entry, stop, target, pts, lines, form=False):
        out.append(dict(kind=kind, s=s, e=e, brk=brk, dir=dr, conf=conf, entry=entry, stop=stop, target=target,
                        pts=pts, lines=lines, forming=form))

    for k in scales:
        P = zigzag(h, l, a, k)
        m = len(P)
        for j in range(m):
            # double top / bottom
            if j + 2 < m and j >= 1:
                pre, p0, p1, p2 = P[j - 1], P[j], P[j + 1], P[j + 2]
                sg = p0[2]
                # in "flipped" terms: X1, Y(neck), X2
                x1, yn, x2 = p0[1] * sg, p1[1] * sg, p2[1] * sg
                top = max(x1, x2)
                hgt = top - yn
                A = a[p0[0]]
                ok = hgt >= 3 * A and abs(x1 - x2) <= 0.12 * hgt and p2[0] - p0[0] >= 8 and pre[1] * sg < yn - 0.3 * hgt
                if ok:
                    for i in range(p0[0], p2[0] + 1):
                        if (h[i] if sg == 1 else -l[i]) > top + 1e-9:
                            ok = False
                            break
                if ok:
                    trip = j + 4 < m and abs(P[j + 4][1] * sg - x1) <= 0.12 * hgt and P[j + 3][1] * sg > yn - 0.25 * hgt
                    lim = p2[0] + (p2[0] - p0[0]) + 3
                    brk = first_close(c, p2[0] + 1, lim, 0.0, p1[1], -sg, 0.1 * A, n)
                    end = brk if brk >= 0 else n - 1
                    clean = all((h[i] if sg == 1 else -l[i]) <= top for i in range(p2[0] + 1, end + 1))
                    names = ['Top 1', 'Neck', 'Top 2'] if sg == 1 else ['Bottom 1', 'Neck', 'Bottom 2']
                    pts = [(p0[0], p0[1], names[0]), (p1[0], p1[1], names[1]), (p2[0], p2[1], names[2])]
                    kind = K['double_top'] if sg == 1 else K['double_bottom']
                    # causal: a third top only counts if it was already confirmed when the double top confirmed
                    trip_c = trip and P[j + 4][3] <= max(brk, p2[3])
                    if brk >= 0 and clean and not trip_c:
                        add(kind, pre[0], brk, brk, -sg, max(brk, p2[3]), c[brk], top * sg, (yn - hgt) * sg, pts, [(p0[0], p1[1], brk, p1[1])])
                    elif forming and brk < 0 and lim > n - 1 and clean and not trip:
                        add(kind, pre[0], n - 1, -1, -sg, p2[3], 0.0, top * sg, (yn - hgt) * sg, pts, [(p0[0], p1[1], n - 1, p1[1])], True)
            # triple top / bottom, head and shoulders
            if j + 4 < m and j >= 1:
                pre = P[j - 1]
                q = P[j:j + 5]
                sg = q[0][2]
                X = [p[1] * sg for p in q]
                peaks = [X[0], X[2], X[4]]
                troughs = [X[1], X[3]]
                hgt = max(peaks) - min(troughs)
                A = a[q[0][0]]
                span = q[4][0] - q[0][0]
                legs = min(q[t + 1][0] - q[t][0] for t in range(4))
                if hgt >= 3 * A and span >= 15 and pre[1] * sg < min(troughs) - 0.3 * hgt and legs >= max(3, 0.1 * span):
                    if (max(peaks) - min(peaks) <= 0.12 * hgt and abs(troughs[0] - troughs[1]) <= 0.25 * hgt
                            and min(q[2][0] - q[0][0], q[4][0] - q[2][0]) >= 5):
                        neck = min(troughs)
                        lim = q[4][0] + int(0.6 * span) + 3
                        brk = first_close(c, q[4][0] + 1, lim, 0.0, neck * sg, -sg, 0.1 * A, n)
                        ext = max(peaks)
                        end = brk if brk >= 0 else n - 1
                        clean = all((h[i] if sg == 1 else -l[i]) <= ext for i in range(q[4][0] + 1, end + 1))
                        lab = ['Top 1', 'Low', 'Top 2', 'Low', 'Top 3'] if sg == 1 else ['Bottom 1', 'High', 'Bottom 2', 'High', 'Bottom 3']
                        pts = [(p[0], p[1], lb) for p, lb in zip(q, lab)]
                        kind = K['triple_top'] if sg == 1 else K['triple_bottom']
                        if brk >= 0 and clean:
                            add(kind, pre[0], brk, brk, -sg, max(brk, q[4][3]), c[brk], ext * sg, (neck - hgt) * sg, pts, [(q[0][0], neck * sg, brk, neck * sg)])
                        elif forming and brk < 0 and lim > n - 1 and clean:
                            add(kind, pre[0], n - 1, -1, -sg, q[4][3], 0.0, ext * sg, (neck - hgt) * sg, pts, [(q[0][0], neck * sg, n - 1, neck * sg)], True)
                    LS, HD, RS = X[0], X[2], X[4]
                    head_h = HD - (troughs[0] + troughs[1]) / 2
                    if (HD - max(LS, RS) >= 0.2 * head_h and abs(LS - RS) <= 0.3 * head_h
                            and abs(troughs[0] - troughs[1]) <= 0.3 * head_h and head_h >= 3 * A
                            and min(LS, RS) - max(troughs) >= 0.25 * head_h
                            and 0.4 <= (q[2][0] - q[0][0]) / max(1, q[4][0] - q[2][0]) <= 2.5):
                        ms = (q[3][1] - q[1][1]) / (q[3][0] - q[1][0])
                        bs = q[1][1] - ms * q[1][0]
                        lim = q[4][0] + int(0.5 * span) + 3
                        brk = first_close(c, q[4][0] + 1, lim, ms, bs, -sg, 0.1 * A, n)
                        end = brk if brk >= 0 else n - 1
                        clean = all((h[i] if sg == 1 else -l[i]) <= q[4][1] * sg for i in range(q[4][0] + 1, end + 1))
                        lab = ['Left shoulder', 'Neck', 'Head', 'Neck', 'Right shoulder']
                        pts = [(p[0], p[1], lb) for p, lb in zip(q, lab)]
                        kind = K['head_shoulders'] if sg == 1 else K['inv_head_shoulders']
                        if brk >= 0 and clean:
                            nb = ms * brk + bs
                            add(kind, pre[0], brk, brk, -sg, max(brk, q[4][3]), c[brk], q[4][1], nb - sg * head_h, pts, [(q[0][0], ms * q[0][0] + bs, brk, nb)])
                        elif forming and brk < 0 and lim > n - 1 and clean:
                            nb = ms * (n - 1) + bs
                            add(kind, pre[0], n - 1, -1, -sg, q[4][3], 0.0, q[4][1], nb - sg * head_h, pts, [(q[0][0], ms * q[0][0] + bs, n - 1, nb)], True)
            # line patterns
            for cnt in (5, 6, 7):
                if j + cnt > m or j < 1:
                    continue
                q = P[j:j + cnt]
                pre = P[j - 1]
                hx = [p[0] for p in q if p[2] == 1]; hy = [p[1] for p in q if p[2] == 1]
                lx = [p[0] for p in q if p[2] == -1]; ly = [p[1] for p in q if p[2] == -1]
                if len(hx) < 2 or len(lx) < 2:
                    continue
                s0, s1 = q[0][0], q[-1][0]
                span = s1 - s0
                if span < 12:
                    continue
                mh, bh = linfit(hx, hy)
                ml, bl = linfit(lx, ly)
                rh = 0.0 if len(hx) == 2 else max(abs(y - (mh * x + bh)) for x, y in zip(hx, hy))
                rl = 0.0 if len(lx) == 2 else max(abs(y - (ml * x + bl)) for x, y in zip(lx, ly))
                w0 = (mh * s0 + bh) - (ml * s0 + bl)
                w1 = (mh * s1 + bh) - (ml * s1 + bl)
                A = a[s0]
                if w0 <= 0 or w1 <= 0 or max(w0, w1) < 3 * A:
                    continue
                W = max(w0, w1)
                if rh > 0.12 * W or rl > 0.12 * W:
                    continue
                bad = False
                for i in range(s0, s1 + 1):
                    fh, fl = mh * i + bh, ml * i + bl
                    if c[i] > fh + 0.1 * W or c[i] < fl - 0.1 * W or h[i] > fh + 0.2 * W or l[i] < fl - 0.2 * W:
                        bad = True
                        break
                if bad:
                    continue
                qn = max(3, span // 4)
                for (u0, u1) in ((s0, s0 + qn), (s1 - qn, s1)):
                    dl = min(l[i] - (ml * i + bl) for i in range(u0, u1 + 1))
                    dh = min((mh * i + bh) - h[i] for i in range(u0, u1 + 1))
                    if dl > 0.15 * W or dh > 0.15 * W:
                        bad = True
                if bad:
                    continue
                nh = mh * span / W
                nl = ml * span / W
                ratio = w1 / w0
                FLAT = 0.12
                kind = -1
                if abs(nh) < FLAT and nl > 0.3 and ratio < 0.6: kind = K['asc_triangle']
                elif abs(nl) < FLAT and nh < -0.3 and ratio < 0.6: kind = K['desc_triangle']
                elif nh < -0.25 and nl > 0.25 and ratio < 0.55: kind = K['sym_triangle']
                elif nh > 0.2 and nl > 0.2 and nl > nh and ratio < 0.6: kind = K['rising_wedge']
                elif nh < -0.2 and nl < -0.2 and nh < nl and ratio < 0.6: kind = K['falling_wedge']
                elif abs(nh) < FLAT and abs(nl) < FLAT and 0.75 < ratio < 1.33 and cnt >= 6: kind = K['rectangle']
                elif nh > 0.25 and nl < -0.25 and ratio > 1.6: kind = K['broadening']
                elif nh > 0.6 and nl > 0.6 and 0.8 < ratio < 1.25 and cnt >= 6: kind = K['channel_up']
                elif nh < -0.6 and nl < -0.6 and 0.8 < ratio < 1.25 and cnt >= 6: kind = K['channel_down']
                if kind < 0:
                    continue
                if kind == K['rising_wedge'] and not pre[1] < ml * s0 + bl:
                    continue
                if kind == K['falling_wedge'] and not pre[1] > mh * s0 + bh:
                    continue
                lim = s1 + max(5, int(0.6 * span))
                bu = first_close(c, s1 + 1, lim, mh, bh, 1, 0.1 * A, n)
                bd = first_close(c, s1 + 1, lim, ml, bl, -1, 0.1 * A, n)
                expected = {K['asc_triangle']: 1, K['desc_triangle']: -1, K['rising_wedge']: -1, K['falling_wedge']: 1,
                            K['channel_up']: -1, K['channel_down']: 1}.get(kind, 0)
                pts = [(p[0], p[1], 'High' if p[2] == 1 else 'Low') for p in q]
                if bu < 0 and bd < 0:
                    if forming and lim > n - 1:
                        e = n - 1
                        dr = expected
                        add(kind, s0, e, -1, dr, q[-1][3], 0.0, 0.0, 0.0, pts, [(s0, mh * s0 + bh, e, mh * e + bh), (s0, ml * s0 + bl, e, ml * e + bl)], True)
                    continue
                if bd < 0 or (bu >= 0 and bu < bd):
                    brk, dr = bu, 1
                else:
                    brk, dr = bd, -1
                if expected != 0 and dr != expected:
                    continue
                ref = (mh * brk + bh) if dr == 1 else (ml * brk + bl)
                tgt_h = w1 if kind == K['broadening'] else w0
                stop = (ml * brk + bl) if dr == 1 else (mh * brk + bh)
                if kind == K['rising_wedge']:
                    stop = max(hy)
                if kind == K['falling_wedge']:
                    stop = min(ly)
                add(kind, s0, brk, brk, dr, max(brk, q[-1][3]), c[brk], stop, ref + dr * tgt_h, pts,
                    [(s0, mh * s0 + bh, brk, mh * brk + bh), (s0, ml * s0 + bl, brk, ml * brk + bl)])
            # flags and pennants
            if j + 1 < m:
                ps, pe = P[j], P[j + 1]
                dr = 1 if pe[2] == 1 else -1
                plen = pe[0] - ps[0]
                pole = abs(pe[1] - ps[1])
                A = a[ps[0]]
                if 2 <= plen <= 15 and pole >= 5 * A and pole >= 1.5 * plen * A * 0.6:
                    best = -1
                    reached_end = False
                    for L in range(5, 26):
                        e = pe[0] + L
                        if e + 1 >= n:
                            reached_end = True
                            break
                        hmax = max(h[pe[0] + 1:e + 1]); lmin = min(l[pe[0] + 1:e + 1])
                        if dr == 1 and (hmax > pe[1] or pe[1] - lmin > 0.5 * pole):
                            break
                        if dr == -1 and (lmin < pe[1] or hmax - pe[1] > 0.5 * pole):
                            break
                        best = e
                    if best < 0:
                        continue
                    found = None
                    mh = bh = ml = bl = 0.0
                    for e in range(pe[0] + 5, best + 1):
                        mh, bh, ml, bl = flag_lines(h, l, pe, e, dr)
                        nb = e + 1
                        if nb >= n:
                            break
                        if dr == 1 and c[nb] > mh * nb + bh + 0.1 * A and c[nb] > h[e]:
                            found = (e, nb); break
                        if dr == -1 and c[nb] < ml * nb + bl - 0.1 * A and c[nb] < l[e]:
                            found = (e, nb); break
                    form = False
                    if found is None:
                        # still pausing at the latest candle -> forming
                        if not (forming and reached_end and best == n - 2 and best - pe[0] >= 5):
                            continue
                        e, nb = best, n - 1
                        mh, bh, ml, bl = flag_lines(h, l, pe, e, dr)
                        form = True
                    else:
                        e, nb = found
                    s0 = pe[0]
                    w0 = (mh * s0 + bh) - (ml * s0 + bl)
                    w1 = (mh * e + bh) - (ml * e + bl)
                    if w0 <= 0 or w1 <= 0 or w0 > 0.6 * pole:
                        continue
                    span = e - s0
                    nh, nl = mh * span / w0, ml * span / w0
                    if w1 / w0 < 0.6 and nh * nl < 0:
                        kind = K['bull_pennant'] if dr == 1 else K['bear_pennant']
                    elif 0.6 <= w1 / w0 <= 1.5 and nh * dr < 0 and nl * dr < 0:
                        kind = K['bull_flag'] if dr == 1 else K['bear_flag']
                    else:
                        continue
                    pts = [(ps[0], ps[1], 'Pole start'), (pe[0], pe[1], 'Pole top' if dr == 1 else 'Pole bottom')]
                    lines = [(s0, mh * s0 + bh, nb, mh * nb + bh), (s0, ml * s0 + bl, nb, ml * nb + bl), (ps[0], ps[1], pe[0], pe[1])]
                    if form:
                        add(kind, ps[0], nb, -1, dr, pe[3], 0.0, 0.0, 0.0, pts, lines, True)
                    else:
                        add(kind, ps[0], nb, nb, dr, max(nb, pe[3]), c[nb], (ml * nb + bl) if dr == 1 else (mh * nb + bh), c[nb] + dr * pole, pts, lines)
        for sg in (1, -1):
            cups(h, l, c, a, k, sg, add, forming, n)
    return [r for r in dedupe(out) if r['s'] >= warm], a


def flag_lines(h, l, pe, e, dr):
    xs = list(range(pe[0] + 1, e + 1))
    if dr == 1:
        mh = max((h[i] - pe[1]) / (i - pe[0]) for i in xs)
        bh = pe[1] - mh * pe[0]
        ml, bl = linfit(xs, [l[i] for i in xs])
        bl += min(l[i] - (ml * i + bl) for i in xs)
    else:
        ml = min((l[i] - pe[1]) / (i - pe[0]) for i in xs)
        bl = pe[1] - ml * pe[0]
        mh, bh = linfit(xs, [h[i] for i in xs])
        bh += max(h[i] - (mh * i + bh) for i in xs)
    return mh, bh, ml, bl


def quadfit(xs, ys):
    """least squares parabola y = a x^2 + b x + c via normal equations"""
    n = len(xs)
    s1 = sum(xs); s2 = sum(x ** 2 for x in xs); s3 = sum(x ** 3 for x in xs); s4 = sum(x ** 4 for x in xs)
    t0 = sum(ys); t1 = sum(x * y for x, y in zip(xs, ys)); t2 = sum(x * x * y for x, y in zip(xs, ys))
    M = [[s4, s3, s2, t2], [s3, s2, s1, t1], [s2, s1, n, t0]]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        for r in range(3):
            if r != col:
                f = M[r][col] / M[col][col]
                for cc in range(col, 4):
                    M[r][cc] -= f * M[col][cc]
    return M[0][3] / M[0][0], M[1][3] / M[1][1], M[2][3] / M[2][2]


def cups(h0, l0, c0, a, k, sg, add, forming, n):
    if sg == 1:
        h, l, c = h0, l0, c0
        P = zigzag(h0, l0, a, k)
    else:
        h, l, c = -l0, -h0, -c0
        P = [(i, -p, -t, cf) for i, p, t, cf in zigzag(h0, l0, a, k)]
    for j in range(len(P) - 2):
        Lr, B, Rr = P[j], P[j + 1], P[j + 2]
        if not (Lr[2] == 1 and B[2] == -1 and Rr[2] == 1):
            continue
        width = Rr[0] - Lr[0]
        depth = min(Lr[1], Rr[1]) - B[1]
        A = a[Lr[0]]
        if width < 20 or depth < 3.5 * A:
            continue
        if Rr[1] > Lr[1] + 0.1 * depth or Rr[1] < Lr[1] - 0.15 * depth:
            continue
        xs = [(i - Lr[0]) / width for i in range(Lr[0], Rr[0] + 1)]
        cc = [(h[i] + l[i]) / 2 for i in range(Lr[0], Rr[0] + 1)]
        qa, qb, qc = quadfit(xs, cc)
        if qa <= 0:
            continue
        vx = -qb / (2 * qa)
        mean = sum(cc) / len(cc)
        ssr = sum((y - (qa * x * x + qb * x + qc)) ** 2 for x, y in zip(xs, cc))
        sst = sum((y - mean) ** 2 for y in cc)
        r2 = 1 - ssr / sst
        if r2 < 0.65 or not 0.3 <= vx <= 0.7:
            continue
        low3 = sum(1 for i in range(Lr[0], Rr[0] + 1) if l[i] < B[1] + depth / 3)
        if low3 / len(cc) < 0.3:
            continue
        rim = max(Lr[1], Rr[1])
        if max(h[Lr[0]:Rr[0] + 1]) > rim + 1e-9:
            continue
        lim = Rr[0] + max(5, int(0.4 * width))
        brk = -1
        for i in range(Rr[0] + 1, min(lim, n)):
            if c[i] > rim + 0.1 * A:
                brk = i
                break
        g = lambda v: sg * v
        pts = [(Lr[0], g(Lr[1]), 'Left rim'), (B[0], g(B[1]), 'Cup bottom' if sg == 1 else 'Cup top'), (Rr[0], g(Rr[1]), 'Right rim')]
        if brk < 0:
            if forming and lim > n - 1:
                e = n - 1
                hl = min(l[Rr[0]:e + 1])
                if rim - hl <= 0.5 * depth:
                    kind = K['cup_handle'] if sg == 1 else K['inv_cup_handle']
                    add(kind, Lr[0], e, -1, sg, Rr[3], 0.0, g(hl), g(rim + depth), pts, [(Lr[0], g(rim), e, g(rim))], True)
            continue
        hl = min(l[Rr[0]:brk + 1])
        hlen = brk - Rr[0]
        if hlen >= max(3, 0.08 * width) and rim - hl >= 0.12 * depth and rim - hl <= 0.5 * depth:
            hi_ = Rr[0] + int(np.argmin(l[Rr[0]:brk + 1]))
            pts.append((hi_, g(hl), 'Handle'))
            kind = K['cup_handle'] if sg == 1 else K['inv_cup_handle']
            add(kind, Lr[0], brk, brk, sg, max(brk, Rr[3]), sg * c[brk], g(hl), g(rim + depth), pts, [(Lr[0], g(rim), brk, g(rim))])
        elif hlen <= max(3, 0.08 * width) + 2:
            kind = K['rounding_bottom'] if sg == 1 else K['rounding_top']
            add(kind, Lr[0], brk, brk, sg, max(brk, Rr[3]), sg * c[brk], g(B[1] + depth * 0.5), g(rim + depth), pts, [(Lr[0], g(rim), brk, g(rim))])


def dedupe(recs):
    """causal: confirmed patterns in order of confirmation (then longer first); a pattern is dropped when it overlaps
    an already kept one of the same kind by more than 40% of the shorter. Forming patterns come last."""
    order = sorted(range(len(recs)), key=lambda i: (recs[i]['forming'], recs[i]['conf'], -(recs[i]['e'] - recs[i]['s']), i))
    kept = []
    for i in order:
        r = recs[i]
        ok = True
        for q in kept:
            if q['kind'] != r['kind']:
                continue
            ov = min(q['e'], r['e']) - max(q['s'], r['s'])
            if ov > 0.4 * min(q['e'] - q['s'], r['e'] - r['s']):
                ok = False
                break
        if ok:
            kept.append(r)
    return kept


if __name__ == '__main__':
    import pandas as pd
    df = pd.read_csv(sys.argv[1])
    a0, a1 = int(sys.argv[2]), int(sys.argv[3])
    warm = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    d = df.iloc[a0:a1]
    recs, _ = detect(d.open.values, d.high.values, d.low.values, d.close.values, warm=warm)
    for r in sorted(recs, key=lambda r: (r['s'], r['kind'], r['e'])):
        print(f"P {KINDS[r['kind']]} {r['s']} {r['e']} {r['brk']} {r['dir']} {int(r['forming'])} {r['target']:.2f}")
