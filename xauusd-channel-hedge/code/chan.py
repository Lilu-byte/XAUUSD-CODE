"""Per-bar live channel (same segmentation rules as GoldChannels / seg.py), using only bars before t.
For bar t: stretch start s, regression line of closes s..t-1 extrapolated to t (= channel middle at t),
channel top/bottom offsets = largest high / lowest low residual vs the line, label (1 up, -1 down, 0 range)."""
import numpy as np, pandas as pd
from seg import atr

def load(path):
    d = pd.read_csv(path)
    d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    return d

def live(d, L=20, buf=0.2, k=2.0, ratio=0.6):
    o, h, l, c = [d[x].values.astype(float) for x in ('open', 'high', 'low', 'close')]
    a = atr(h, l, c, 14); N = len(c)
    S = np.full(N, -1); MID = np.full(N, np.nan); UP = np.full(N, np.nan); LO = np.full(N, np.nan)
    LAB = np.zeros(N, int); BRK = np.zeros(N, bool)
    s = 0
    for t in range(1, N):
        n = t - s
        if n >= 2:
            x = np.arange(n); y = c[s:t]
            b, a0 = np.polyfit(x, y, 1); line = a0 + b * x
            mid_t = a0 + b * n
            up = (h[s:t] - line).max(); lo = (l[s:t] - line).min()
            S[t] = s; MID[t] = mid_t; UP[t] = up; LO[t] = lo
            LAB[t] = 0 if abs(b * (n - 1)) < ratio * (up - lo) else (1 if b > 0 else -1)
            if n >= L:
                sd = (y - line).std()
                dd = 1 if c[t] > mid_t + k * sd + buf * a[t] else (-1 if c[t] < mid_t - k * sd - buf * a[t] else 0)
                if dd:
                    w0 = max(s + L // 2, t - L + 1)
                    p = w0 + (np.argmin(l[w0:t+1]) if dd == 1 else np.argmax(h[w0:t+1]))
                    BRK[t] = True; s = p
    return pd.DataFrame(dict(s=S, n=np.arange(N) - S, mid=MID, up=UP, lo=LO, lab=LAB, brk=BRK), index=d.index)

if __name__ == '__main__':
    import sys
    for tf in sys.argv[1:]:
        d = load(f'data/XAUUSD_{tf}.csv'); ch = live(d)
        out = pd.concat([d[['open', 'high', 'low', 'close', 'spread']], ch], axis=1)
        out.to_pickle(f'live_{tf}.pkl'); print(tf, len(out), out.brk.sum())
