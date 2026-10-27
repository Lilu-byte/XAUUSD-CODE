"""Detect classic chart patterns in real XAUUSD history (MT5 export).
Output: patterns.json with one record per instance (timeframe, bar range, key points, lines, breakout)."""
import json, sys
import numpy as np, pandas as pd

D = '/mnt/project-files/'
FILES = {'D1': D + 'xauusd-price-action/data/XAUUSD_D1.csv',
         'H4': D + 'xauusd-price-action/data/XAUUSD_H4.csv',
         'H1': D + 'xauusd-price-action/data/XAUUSD_H1.csv',
         'M15': D + 'xauusd-intraday/data/XAUUSD_M15.csv',
         'M5': D + 'xauusd-intraday/data/XAUUSD_M5.csv'}


def load(tf):
    df = pd.read_csv(FILES[tf])
    df['time'] = pd.to_datetime(df['time'], format='%Y.%m.%d %H:%M')
    return df.reset_index(drop=True)


def atr(df, n=14):
    h, l, c = df.high.values, df.low.values, df.close.values
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().values


def zigzag(df, a, k):
    """Alternating swing highs/lows; a swing is confirmed once price reverses k*ATR.
    Returns list of (idx, price, +1 high / -1 low, confirm_idx)."""
    h, l = df.high.values, df.low.values
    piv = []
    d = 0
    ei, ep = 0, h[0]
    li, lp = 0, l[0]
    for i in range(1, len(h)):
        if d >= 0:  # looking for high (or undecided)
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


def fit(points):
    x = np.array([p[0] for p in points], float)
    y = np.array([p[1] for p in points], float)
    if len(x) == 2:
        m = (y[1] - y[0]) / (x[1] - x[0])
        return m, y[0] - m * x[0], 0.0
    m, b = np.polyfit(x, y, 1)
    res = np.abs(y - (m * x + b)).max()
    return m, b, res


def first_close_beyond(c, start, end, f, side, margin):
    """first bar in [start,end) whose close is above (side=1) / below (side=-1) f(i) +- margin"""
    for i in range(start, min(end, len(c))):
        if side == 1 and c[i] > f(i) + margin:
            return i
        if side == -1 and c[i] < f(i) - margin:
            return i
    return None


def detect_tf(tf):
    df = load(tf)
    a = atr(df)
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    n = len(c)
    out = []

    def add(kind, s, e, brk, direction, points, lines, extra=None):
        rec = dict(tf=tf, kind=kind, s=int(s), e=int(e), brk=None if brk is None else int(brk),
                   dir=int(direction), pts=[[int(i), round(float(p), 2), lab] for i, p, lab in points],
                   lines=[[int(x1), round(float(y1), 2), int(x2), round(float(y2), 2)] for x1, y1, x2, y2 in lines],
                   atr=round(float(a[s]), 2))
        if extra:
            rec.update(extra)
        out.append(rec)

    for k in (1.5, 2.0, 3.0, 4.5):
        P = zigzag(df, a, k)
        m = len(P)
        for j in range(m):
            # ---------- double / triple tops & bottoms, head & shoulders ----------
            # pattern starting at pivot j with alternating highs/lows
            if j + 2 < m:
                p0, p1, p2 = P[j], P[j + 1], P[j + 2]
                if j >= 1:
                    pre = P[j - 1]
                else:
                    pre = None
                if p0[2] == 1:  # H L H -> double top
                    H1, L1, H2 = p0, p1, p2
                    hgt = max(H1[1], H2[1]) - L1[1]
                    A = a[H1[0]]
                    if (hgt >= 3 * A and abs(H1[1] - H2[1]) <= 0.12 * hgt and H2[0] - H1[0] >= 8
                            and pre is not None and pre[1] < L1[1] - 0.3 * hgt
                            and h[H1[0]:H2[0] + 1].max() <= max(H1[1], H2[1]) + 1e-9):
                        # not triple: next high must not again match
                        trip = j + 4 < m and abs(P[j + 4][1] - H1[1]) <= 0.12 * hgt and P[j + 3][1] > L1[1] - 0.25 * hgt
                        lim = H2[0] + int(1.0 * (H2[0] - H1[0])) + 3
                        brk = first_close_beyond(c, H2[0] + 1, lim, lambda i: L1[1], -1, 0.1 * A)
                        if brk is not None and h[H2[0] + 1:brk + 1].max() <= max(H1[1], H2[1]) and not trip:
                            add('double_top', pre[0], brk, brk, -1,
                                [(H1[0], H1[1], 'Top 1'), (L1[0], L1[1], 'Neck'), (H2[0], H2[1], 'Top 2')],
                                [(H1[0], L1[1], brk, L1[1])],
                                dict(entry=c[brk], stop=max(H1[1], H2[1]), target=L1[1] - hgt, conf=max(brk, H2[3])))
                if p0[2] == -1:
                    L1, H1, L2 = p0, p1, p2
                    hgt = H1[1] - min(L1[1], L2[1])
                    A = a[L1[0]]
                    if (hgt >= 3 * A and abs(L1[1] - L2[1]) <= 0.12 * hgt and L2[0] - L1[0] >= 8
                            and pre is not None and pre[1] > H1[1] + 0.3 * hgt
                            and l[L1[0]:L2[0] + 1].min() >= min(L1[1], L2[1]) - 1e-9):
                        trip = j + 4 < m and abs(P[j + 4][1] - L1[1]) <= 0.12 * hgt and P[j + 3][1] < H1[1] + 0.25 * hgt
                        lim = L2[0] + int(1.0 * (L2[0] - L1[0])) + 3
                        brk = first_close_beyond(c, L2[0] + 1, lim, lambda i: H1[1], 1, 0.1 * A)
                        if brk is not None and l[L2[0] + 1:brk + 1].min() >= min(L1[1], L2[1]) and not trip:
                            add('double_bottom', pre[0], brk, brk, 1,
                                [(L1[0], L1[1], 'Bottom 1'), (H1[0], H1[1], 'Neck'), (L2[0], L2[1], 'Bottom 2')],
                                [(L1[0], H1[1], brk, H1[1])],
                                dict(entry=c[brk], stop=min(L1[1], L2[1]), target=H1[1] + hgt, conf=max(brk, L2[3])))
            if j + 4 < m and j >= 1:
                pre = P[j - 1]
                q = P[j:j + 5]
                sgn = q[0][2]
                X = [p[1] * sgn for p in q]  # flip so that tops are "highs"
                pre_x = pre[1] * sgn
                peaks = [X[0], X[2], X[4]]
                troughs = [X[1], X[3]]
                hgt = max(peaks) - min(troughs)
                A = a[q[0][0]]
                span = q[4][0] - q[0][0]
                legs = [q[t + 1][0] - q[t][0] for t in range(4)]
                base_ok = (hgt >= 3 * A and span >= 15 and pre_x < min(troughs) - 0.3 * hgt
                           and min(legs) >= max(3, 0.1 * span))
                ext = (h if sgn == 1 else -l)[q[0][0]:q[4][0] + 1]
                ext = ext if sgn == 1 else ext
                if base_ok:
                    # triple top/bottom: three peaks within 12% of height, troughs similar
                    if (max(peaks) - min(peaks) <= 0.12 * hgt and abs(troughs[0] - troughs[1]) <= 0.25 * hgt
                            and min(q[2][0] - q[0][0], q[4][0] - q[2][0]) >= 5):
                        neck = min(troughs)
                        lim = q[4][0] + int(0.6 * span) + 3
                        cf = (lambda i, nk=neck * sgn: nk)
                        brk = first_close_beyond(c, q[4][0] + 1, lim, cf, -sgn, 0.1 * A)
                        if brk is not None:
                            extreme = max(peaks) * sgn
                            seg = h[q[4][0] + 1:brk + 1] if sgn == 1 else l[q[4][0] + 1:brk + 1]
                            if (sgn == 1 and seg.max() <= extreme) or (sgn == -1 and seg.min() >= extreme):
                                lab = ['Top 1', 'Low', 'Top 2', 'Low', 'Top 3'] if sgn == 1 else ['Bottom 1', 'High', 'Bottom 2', 'High', 'Bottom 3']
                                add('triple_top' if sgn == 1 else 'triple_bottom', pre[0], brk, brk, -sgn,
                                    [(p[0], p[1], lb) for p, lb in zip(q, lab)],
                                    [(q[0][0], neck * sgn, brk, neck * sgn)],
                                    dict(entry=c[brk], stop=extreme, target=(neck - hgt) * sgn, conf=max(brk, q[4][3])))
                    # head and shoulders: middle peak clearly highest, shoulders similar
                    LS, HD, RS = X[0], X[2], X[4]
                    sh = max(LS, RS)
                    neck_lo = min(troughs)
                    head_h = HD - (troughs[0] + troughs[1]) / 2
                    if (HD - sh >= 0.2 * head_h and abs(LS - RS) <= 0.3 * head_h
                            and abs(troughs[0] - troughs[1]) <= 0.3 * head_h and head_h >= 3 * A
                            and min(LS, RS) - max(troughs) >= 0.25 * head_h
                            and 0.4 <= (q[2][0] - q[0][0]) / max(1, q[4][0] - q[2][0]) <= 2.5):
                        x1, y1, x2, y2 = q[1][0], q[1][1], q[3][0], q[3][1]
                        ms = (y2 - y1) / (x2 - x1)
                        nf = lambda i, x1=x1, y1=y1, ms=ms: y1 + ms * (i - x1)
                        lim = q[4][0] + int(0.5 * span) + 3
                        brk = first_close_beyond(c, q[4][0] + 1, lim, nf, -sgn, 0.1 * A)
                        if brk is not None:
                            seg = h[q[4][0] + 1:brk + 1] if sgn == 1 else l[q[4][0] + 1:brk + 1]
                            if (sgn == 1 and seg.max() <= q[4][1]) or (sgn == -1 and seg.min() >= q[4][1]):
                                lab = ['Left shoulder', 'Neck', 'Head', 'Neck', 'Right shoulder']
                                add('head_shoulders' if sgn == 1 else 'inv_head_shoulders', pre[0], brk, brk, -sgn,
                                    [(p[0], p[1], lb) for p, lb in zip(q, lab)],
                                    [(q[0][0], nf(q[0][0]), brk, nf(brk))],
                                    dict(entry=c[brk], stop=q[4][1], target=nf(brk) - sgn * head_h, conf=max(brk, q[4][3])))

            # ---------- line patterns: triangles, wedges, rectangles, broadening, channels ----------
            for cnt in (5, 6, 7):
                if j + cnt > m or j < 1:
                    continue
                q = P[j:j + cnt]
                pre = P[j - 1]
                hi = [(p[0], p[1]) for p in q if p[2] == 1]
                lo = [(p[0], p[1]) for p in q if p[2] == -1]
                if len(hi) < 2 or len(lo) < 2:
                    continue
                s0, s1 = q[0][0], q[-1][0]
                span = s1 - s0
                if span < 12:
                    continue
                mh, bh, rh = fit(hi)
                ml, bl, rl = fit(lo)
                fh = lambda i, mh=mh, bh=bh: mh * i + bh
                fl = lambda i, ml=ml, bl=bl: ml * i + bl
                w0 = fh(s0) - fl(s0)
                w1 = fh(s1) - fl(s1)
                A = a[s0]
                if w0 <= 0 or w1 <= 0 or max(w0, w1) < 3 * A:
                    continue
                W = max(w0, w1)
                if rh > 0.12 * W or rl > 0.12 * W:
                    continue
                # price must stay inside lines (closes) between first and last pivot
                ii = np.arange(s0, s1 + 1)
                if (c[ii] > fh(ii) + 0.1 * W).any() or (c[ii] < fl(ii) - 0.1 * W).any():
                    continue
                if (h[ii] > fh(ii) + 0.2 * W).any() or (l[ii] < fl(ii) - 0.2 * W).any():
                    continue
                q1 = np.arange(s0, s0 + max(3, span // 4) + 1)
                q4 = np.arange(s1 - max(3, span // 4), s1 + 1)
                if any((l[qq] - fl(qq)).min() > 0.15 * W or (fh(qq) - h[qq]).min() > 0.15 * W for qq in (q1, q4)):
                    continue
                nh = mh * span / W
                nl = ml * span / W
                ratio = w1 / w0
                FLAT = 0.12
                kind = None
                if abs(nh) < FLAT and nl > 0.3 and ratio < 0.6:
                    kind = 'asc_triangle'
                elif abs(nl) < FLAT and nh < -0.3 and ratio < 0.6:
                    kind = 'desc_triangle'
                elif nh < -0.25 and nl > 0.25 and ratio < 0.55:
                    kind = 'sym_triangle'
                elif nh > 0.2 and nl > 0.2 and nl > nh and ratio < 0.6:
                    kind = 'rising_wedge'
                elif nh < -0.2 and nl < -0.2 and nh < nl and ratio < 0.6:
                    kind = 'falling_wedge'
                elif abs(nh) < FLAT and abs(nl) < FLAT and 0.75 < ratio < 1.33 and cnt >= 6:
                    kind = 'rectangle'
                elif nh > 0.25 and nl < -0.25 and ratio > 1.6:
                    kind = 'broadening'
                elif nh > 0.6 and nl > 0.6 and 0.8 < ratio < 1.25 and cnt >= 6:
                    kind = 'channel_up'
                elif nh < -0.6 and nl < -0.6 and 0.8 < ratio < 1.25 and cnt >= 6:
                    kind = 'channel_down'
                if kind is None:
                    continue
                # wedges / channels / triangles need a fitting prior move
                if kind == 'rising_wedge' and not pre[1] < fl(s0):
                    continue
                if kind == 'falling_wedge' and not pre[1] > fh(s0):
                    continue
                lim = s1 + max(5, int(0.6 * span))
                bu = first_close_beyond(c, s1 + 1, lim, fh, 1, 0.1 * A)
                bd = first_close_beyond(c, s1 + 1, lim, fl, -1, 0.1 * A)
                if bu is None and bd is None:
                    continue
                if bd is None or (bu is not None and bu < bd):
                    brk, dr = bu, 1
                else:
                    brk, dr = bd, -1
                # expected break side (others accept both and record it)
                expected = {'asc_triangle': 1, 'desc_triangle': -1, 'rising_wedge': -1, 'falling_wedge': 1,
                            'channel_up': -1, 'channel_down': 1}.get(kind)
                if expected is not None and dr != expected:
                    continue
                # pattern height at start; target = height projected from break level
                ref = fh(brk) if dr == 1 else fl(brk)
                tgt_h = w0 if kind not in ('broadening',) else w1
                if kind in ('rising_wedge', 'falling_wedge', 'channel_up', 'channel_down'):
                    tgt_h = w0
                stop = fl(brk) if dr == 1 else fh(brk)
                if kind in ('rising_wedge',):
                    stop = max(p[1] for p in hi)
                if kind in ('falling_wedge',):
                    stop = min(p[1] for p in lo)
                lb = {1: 'High', -1: 'Low'}
                add(kind, s0, brk, brk, dr,
                    [(p[0], p[1], lb[p[2]]) for p in q],
                    [(s0, fh(s0), brk, fh(brk)), (s0, fl(s0), brk, fl(brk))],
                    dict(entry=c[brk], stop=stop, target=ref + dr * tgt_h, conf=max(brk, q[-1][3]), npiv=cnt))

            # ---------- flags & pennants: a sharp pole then a small pause ----------
            if j + 1 < m:
                ps, pe = P[j], P[j + 1]
                dr = 1 if pe[2] == 1 else -1
                plen = pe[0] - ps[0]
                pole = abs(pe[1] - ps[1])
                A = a[ps[0]]
                if 2 <= plen <= 15 and pole >= 5 * A and pole >= 1.5 * plen * A * 0.6:
                    # consolidation after pole end
                    best = None
                    for L in range(5, 26):
                        e = pe[0] + L
                        if e + 1 >= n:
                            break
                        seg_h = h[pe[0] + 1:e + 1]
                        seg_l = l[pe[0] + 1:e + 1]
                        if dr == 1:
                            if seg_h.max() > pe[1] or pe[1] - seg_l.min() > 0.5 * pole:
                                break
                        else:
                            if seg_l.min() < pe[1] or seg_h.max() - pe[1] > 0.5 * pole:
                                break
                        best = e
                    if best is None:
                        continue
                    # look for breakout after a pause of >=5 bars: fit lines on consolidation highs/lows
                    found = None
                    for e in range(pe[0] + 5, best + 1):
                        idx = np.arange(pe[0] + 1, e + 1)
                        # line through the pole tip touching the pause from outside, other side fitted then shifted
                        if dr == 1:
                            mh = ((h[idx] - pe[1]) / (idx - pe[0])).max()
                            bh = pe[1] - mh * pe[0]
                            ml, bl = np.polyfit(idx, l[idx], 1)
                            bl += (l[idx] - (ml * idx + bl)).min()
                        else:
                            ml = ((l[idx] - pe[1]) / (idx - pe[0])).min()
                            bl = pe[1] - ml * pe[0]
                            mh, bh = np.polyfit(idx, h[idx], 1)
                            bh += (h[idx] - (mh * idx + bh)).max()
                        fh = lambda i, mh=mh, bh=bh: mh * i + bh
                        fl = lambda i, ml=ml, bl=bl: ml * i + bl
                        nb = e + 1
                        if nb >= n:
                            break
                        if dr == 1 and c[nb] > fh(nb) + 0.1 * A and c[nb] > h[e]:
                            found = (e, nb, mh, bh, ml, bl)
                            break
                        if dr == -1 and c[nb] < fl(nb) - 0.1 * A and c[nb] < l[e]:
                            found = (e, nb, mh, bh, ml, bl)
                            break
                    if found is None:
                        continue
                    e, nb, mh, bh, ml, bl = found
                    s0 = pe[0]
                    fh = lambda i: mh * i + bh
                    fl = lambda i: ml * i + bl
                    w0, w1 = fh(s0) - fl(s0), fh(e) - fl(e)
                    if w0 <= 0 or w1 <= 0 or w0 > 0.6 * pole:
                        continue
                    span = e - s0
                    nh, nl = mh * span / w0, ml * span / w0
                    if w1 / w0 < 0.6 and nh * nl < 0:  # converging, opposite slopes -> pennant
                        kind = 'bull_pennant' if dr == 1 else 'bear_pennant'
                    elif 0.6 <= w1 / w0 <= 1.5 and nh * dr < 0 and nl * dr < 0:  # parallel, against pole
                        kind = 'bull_flag' if dr == 1 else 'bear_flag'
                    else:
                        continue
                    add(kind, ps[0], nb, nb, dr,
                        [(ps[0], ps[1], 'Pole start'), (pe[0], pe[1], 'Pole top' if dr == 1 else 'Pole bottom')],
                        [(s0, fh(s0), nb, fh(nb)), (s0, fl(s0), nb, fl(nb)), (ps[0], ps[1], pe[0], pe[1])],
                        dict(entry=c[nb], stop=fl(nb) if dr == 1 else fh(nb), target=c[nb] + dr * pole, conf=max(nb, pe[3]), pole=1))

        for sg in (1, -1):
            cups(df, a, k, sg, add)
    return df, a, out


def cups(df, a, k, sg, add):
    """cup & handle and rounding bottom (sg=1); inverted cup & handle and rounding top (sg=-1)."""
    if sg == 1:
        h, l, c = df.high.values, df.low.values, df.close.values
        P = zigzag(df, a, k)
    else:
        h, l, c = -df.low.values, -df.high.values, -df.close.values
        P = [(i, -p, -t, cf) for i, p, t, cf in zigzag(df, a, k)]
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
        idx = np.arange(Lr[0], Rr[0] + 1)
        cc = (h[idx] + l[idx]) / 2
        x = (idx - idx[0]) / width
        co = np.polyfit(x, cc, 2)
        if co[0] <= 0:
            continue
        vx = -co[1] / (2 * co[0])
        pred = np.polyval(co, x)
        r2 = 1 - ((cc - pred) ** 2).sum() / ((cc - cc.mean()) ** 2).sum()
        if r2 < 0.65 or not 0.3 <= vx <= 0.7:
            continue
        if ((l[idx] < B[1] + depth / 3).mean()) < 0.3:
            continue
        rim = max(Lr[1], Rr[1])
        if h[idx].max() > rim + 1e-9:
            continue
        lim = Rr[0] + max(5, int(0.4 * width))
        brk = None
        for i in range(Rr[0] + 1, min(lim, len(c))):
            if c[i] > rim + 0.1 * A:
                brk = i
                break
        if brk is None:
            continue
        hseg = l[Rr[0]:brk + 1]
        hl = hseg.min()
        hlen = brk - Rr[0]
        g = lambda v: sg * v
        pts = [(Lr[0], g(Lr[1]), 'Left rim'), (B[0], g(B[1]), 'Cup bottom' if sg == 1 else 'Cup top'), (Rr[0], g(Rr[1]), 'Right rim')]
        curve = [[int(i), round(float(g(np.polyval(co, (i - idx[0]) / width))), 2)] for i in idx[::max(1, width // 30)]] + \
                [[int(idx[-1]), round(float(g(np.polyval(co, 1.0))), 2)]]
        entry = sg * c[brk]
        if hlen >= max(3, 0.08 * width) and rim - hl >= 0.12 * depth and rim - hl <= 0.5 * depth:
            hi_ = Rr[0] + int(np.argmin(hseg))
            pts.append((hi_, g(hl), 'Handle'))
            add('cup_handle' if sg == 1 else 'inv_cup_handle', Lr[0], brk, brk, sg, pts, [(Lr[0], g(rim), brk, g(rim))],
                dict(entry=entry, stop=g(hl), target=g(rim + depth), conf=max(brk, Rr[3]), curve=curve))
        elif hlen <= max(3, 0.08 * width) + 2:
            add('rounding_bottom' if sg == 1 else 'rounding_top', Lr[0], brk, brk, sg, pts, [(Lr[0], g(rim), brk, g(rim))],
                dict(entry=entry, stop=g(B[1] + depth * 0.5), target=g(rim + depth), conf=max(brk, Rr[3]), curve=curve))


def dedupe(recs):
    """drop instances of the same kind that overlap >50% with an earlier kept one (prefer larger)."""
    recs = sorted(recs, key=lambda r: -(r['e'] - r['s']))
    kept = []
    for r in recs:
        ok = True
        for k in kept:
            if k['kind'] != r['kind'] or k['tf'] != r['tf']:
                continue
            ov = min(k['e'], r['e']) - max(k['s'], r['s'])
            if ov > 0.4 * min(k['e'] - k['s'], r['e'] - r['s']):
                ok = False
                break
        if ok:
            kept.append(r)
    return kept


def outcome(df, a, r):
    """trade from the bar after confirmation: hit target first (+R), stop first (-1), or time out."""
    h, l, c = df.high.values, df.low.values, df.close.values
    i0 = r['conf']
    if i0 + 1 >= len(c):
        return None
    entry = c[i0]
    d = r['dir']
    stop, tgt = r['stop'], r['target']
    risk = (entry - stop) * d
    rew = (tgt - entry) * d
    if risk <= 0.2 * a[i0] or rew <= 0:
        return None
    horizon = max(20, 3 * (r['e'] - r['s']))
    res = 0.0
    for i in range(i0 + 1, min(len(c), i0 + 1 + horizon)):
        if (d == 1 and l[i] <= stop) or (d == -1 and h[i] >= stop):
            return dict(R=-1.0, hit=0, rr=rew / risk, risk=risk, entry=entry, i0=i0, horizon=horizon)
        if (d == 1 and h[i] >= tgt) or (d == -1 and l[i] <= tgt):
            return dict(R=rew / risk, hit=1, rr=rew / risk, risk=risk, entry=entry, i0=i0, horizon=horizon)
        res = (c[i] - entry) * d / risk
    return dict(R=res, hit=0.5, rr=rew / risk, risk=risk, entry=entry, i0=i0, horizon=horizon)


if __name__ == '__main__':
    allr = []
    frames = {}
    for tf in FILES:
        df, a, recs = detect_tf(tf)
        recs = dedupe(recs)
        frames[tf] = (df, a)
        for r in recs:
            r['out'] = outcome(df, a, r)
        allr += recs
        print(tf, len(df), len(recs), pd.Series([r['kind'] for r in recs]).value_counts().to_dict(), file=sys.stderr)
    json.dump(allr, open(sys.argv[1] if len(sys.argv) > 1 else 'patterns.json', 'w'), default=float)
