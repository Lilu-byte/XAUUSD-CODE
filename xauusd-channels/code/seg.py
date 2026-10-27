"""Prototype of the channel segmentation used by GoldChannels.mq5 (same rules, closed bars only)."""
import numpy as np, pandas as pd, sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')

def atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    out = np.empty_like(tr); out[0] = tr[0]
    for i in range(1, len(tr)):            # Wilder
        out[i] = out[i-1] + (tr[i] - out[i-1]) / n
    return out

def fit(c, h, l, s, e):
    """regression of closes on bars s..e; returns slope, intercept at s, upper/lower offsets"""
    y = c[s:e+1]; x = np.arange(len(y))
    if len(y) < 2: return 0.0, y[0], h[s]-y[0], l[s]-y[0]
    b, a = np.polyfit(x, y, 1)
    line = a + b * x
    return b, a, (h[s:e+1] - line).max(), (l[s:e+1] - line).min()

def label(b, n, up, lo, ratio):
    move = b * (n - 1); height = up - lo
    if abs(move) < ratio * height: return 0
    return 1 if move > 0 else -1

def band(c, s, e):
    y = c[s:e+1]; x = np.arange(len(y))
    b, a = np.polyfit(x, y, 1)
    return b, a, (y - (a + b * x)).std()

def segment(o, h, l, c, L=20, buf=0.2, ratio=1.0, atrn=14, k=2.0, nc=1, live=None):
    """live: optional array filled with the live stretch's label as of each closed bar (2 = forming)"""
    a = atr(h, l, c, atrn)
    segs = []                      # (start, end, label)
    events = []                    # (break bar, direction, new label at confirmation time)
    s = 0
    t = 1
    N = len(c)
    while t < N:
        if t - s >= L + nc - 1:              # band fitted on s..t-nc (at least L candles), the last nc closes must all be outside
            b, a0, sd = band(c, s, t - nc)
            ups = dns = 0
            for j in range(nc):
                line_j = a0 + b * (t - j - s); g = k * sd + buf * a[t - j]
                ups += c[t - j] > line_j + g; dns += c[t - j] < line_j - g
            d = 1 if ups == nc else -1 if dns == nc else 0
            if d:
                w0 = max(s + L // 2, t - L + 1)
                win = slice(w0, t + 1)
                p = w0 + (np.argmin(l[win]) if d == 1 else np.argmax(h[win]))
                bb, aa, uu, ll = fit(c, h, l, s, p)
                segs.append((s, p, label(bb, p - s + 1, uu, ll, ratio)))
                events.append((t, d))
                s = p
        if live is not None:
            if t - s + 1 < L: live[t] = 2
            else:
                bb, aa, uu, ll = fit(c, h, l, s, t); live[t] = label(bb, t - s + 1, uu, ll, ratio)
        t += 1
    bb, aa, uu, ll = fit(c, h, l, s, N - 1)
    segs.append((s, N - 1, label(bb, N - s, uu, ll, ratio)))
    return segs, events

def quality(c, h, l, s, e, lab, flat=True, tol=0.10):
    """touches of the upper and lower line (separate swings, within tol x width) and R^2 of closes around the line"""
    b, a, up, lo = fit(c, h, l, s, e)
    x = np.arange(e - s + 1); line = a + b * x
    if lab in (0, 2) and flat:
        U = np.full_like(line, h[s:e+1].max()); Lo = np.full_like(line, l[s:e+1].min())
    else:
        U = line + up; Lo = line + lo
    w = (U - Lo)[0]
    tu = h[s:e+1] >= U - tol * w; tl = l[s:e+1] <= Lo + tol * w
    cnt = lambda m: int(np.sum(m[1:] & ~m[:-1]) + m[0])
    y = c[s:e+1]; ss = ((y - y.mean())**2).sum()
    r2 = 1 - ((y - line)**2).sum() / ss if ss > 0 else 0
    return cnt(tu), cnt(tl), r2
