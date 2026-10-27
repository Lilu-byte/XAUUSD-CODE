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

def segment(o, h, l, c, L=20, buf=0.2, ratio=1.0, atrn=14, k=2.0):
    a = atr(h, l, c, atrn)
    segs = []                      # (start, end, label)
    events = []                    # (break bar, direction, new label at confirmation time)
    s = 0
    t = 1
    N = len(c)
    while t < N:
        if t - s >= L:
            b, a0, sd = band(c, s, t - 1)
            line_t = a0 + b * (t - s)
            d = 0
            if c[t] > line_t + k * sd + buf * a[t]: d = 1
            elif c[t] < line_t - k * sd - buf * a[t]: d = -1
            if d:
                w0 = max(s + L // 2, t - L + 1)
                win = slice(w0, t + 1)
                p = w0 + (np.argmin(l[win]) if d == 1 else np.argmax(h[win]))
                bb, aa, uu, ll = fit(c, h, l, s, p)
                segs.append((s, p, label(bb, p - s + 1, uu, ll, ratio)))
                events.append((t, d))
                s = p
        t += 1
    bb, aa, uu, ll = fit(c, h, l, s, N - 1)
    segs.append((s, N - 1, label(bb, N - s, uu, ll, ratio)))
    return segs, events
