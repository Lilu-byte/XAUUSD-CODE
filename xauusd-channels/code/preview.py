"""Draws roughly what GoldChannels.mq5 v1.10 shows (default inputs) on David's exported candles: preview images for the README."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, gbt, seg
UP, DN, RG, FM = '#26a69a', '#ef5350', '#5680d6', '#808080'
MINB = {'M1': 60, 'M5': 40, 'M15': 30, 'M30': 25}
HTF = {'M5': 'H1', 'M15': 'H4', 'H1': 'D1', 'H4': 'D1'}
def shade(col, w=.22, bg=(0, 0, 0)):
    c = matplotlib.colors.to_rgb(col); return tuple(a * w + b * (1 - w) for a, b in zip(c, bg))
def strong(c, h, l, s, e, lab):
    tu, tl, r2 = seg.quality(c, h, l, s, e, lab, tol=0.20)
    return tu >= 2 and tl >= 2 and (lab in (0, 2) or r2 >= 0.6)
def channels(d, tf, hist=3000):
    d = d.iloc[-hist:]; o, h, l, c = [d[k].values for k in ('open', 'high', 'low', 'close')]
    L = MINB.get(tf, 20)
    segs, ev = seg.segment(o, h, l, c, L, 0.2, 0.6, k=2.0, nc=2)
    out = []
    for i, (s, e, lab) in enumerate(segs):
        live = i == len(segs) - 1
        b, a, up, lo = seg.fit(c, h, l, s, e); nn = e - s + 1
        if live: lab = seg.label(b, nn, up, lo, 0.6) if nn >= L else 2
        out.append((s, e, lab, live, b, a, up, lo, h[s:e+1].max(), l[s:e+1].min(), strong(c, h, l, s, e, lab)))
    return d, out, ev
def geom(s, e, lab, live, b, a, up, lo, hh, ll, proj):
    xe = e - s + (proj if live else 0)
    if lab in (0, 2): return xe, np.array([hh, hh]), np.array([ll, ll])
    return xe, a + up + b * np.array([0, xe]), a + lo + b * np.array([0, xe])
def draw(tf, n, out):
    d, ch, ev = channels(gbt.load(tf), tf)
    o, h, l, c = [d[k].values for k in ('open', 'high', 'low', 'close')]
    N = len(c); x0 = N - n
    fig, ax = plt.subplots(figsize=(16, 7)); fig.patch.set_facecolor('black'); ax.set_facecolor('black')
    for s, e, lab, live, b, a, up, lo, hh, ll, st in ch:
        if e < x0: continue
        col = {1: UP, -1: DN, 0: RG, 2: FM}[lab]; faded = not st and lab != 2
        xe, u, lw_ = geom(s, e, lab, live, b, a, up, lo, hh, ll, 10); xs = np.array([s, s + xe])
        ax.fill_between(xs, lw_, u, color=shade(col, .22 * (.45 if faded else 1)), zorder=0)
        lc = shade(col, .55) if faded else col; ls = '--' if live else '-'
        ax.plot(xs, u, ls, color=lc, lw=1.2); ax.plot(xs, lw_, ls, color=lc, lw=1.2); ax.plot(xs, (u + lw_) / 2, ':', color=lc, lw=.8)
        if s >= x0: ax.text(s, u[0], {1: 'UP', -1: 'DOWN', 0: 'RANGE', 2: 'FORMING'}[lab] + (' (live)' if live else ''), color=lc, fontsize=8, va='bottom')
    # higher timeframe, mapped onto this chart's candles by time
    htf = HTF[tf]; dh, chh, _ = channels(gbt.load(htf).loc[:d.index[-1]], htf)
    sec = (dh.index[1:] - dh.index[:-1]).min()
    for s, e, lab, live, b, a, up, lo, hh, ll, st in chh:
        if dh.index[e] < d.index[x0]: continue
        xe, u, lw_ = geom(s, e, lab, live, b, a, up, lo, hh, ll, 2)
        t1, t2 = dh.index[s], dh.index[e] + (sec * 2 if live else sec * 0)
        i1, i2 = np.searchsorted(d.index, t1), np.searchsorted(d.index, t2)
        if live: i2 = N - 1 + (t2 - d.index[-1]) / (d.index[-1] - d.index[-2])
        col = {1: UP, -1: DN, 0: RG, 2: FM}[lab]
        ax.plot([i1, i2], u, '--' if live else '-', color=col, lw=2.6); ax.plot([i1, i2], lw_, '--' if live else '-', color=col, lw=2.6)
        if i1 >= x0: ax.text(i1, u[0], f"{htf} " + {1: 'UP', -1: 'DOWN', 0: 'RANGE', 2: 'FORMING'}[lab] + (' (live)' if live else ''), color=col, fontsize=9, weight='bold', va='bottom')
    for i in range(x0, N):
        cc = UP if c[i] >= o[i] else DN
        ax.vlines(i, l[i], h[i], color=cc, lw=.7); ax.vlines(i, min(o[i], c[i]), max(o[i], c[i]), color=cc, lw=2.2)
    for t, dr in ev:
        if t >= x0: ax.plot(t, l[t] - 0.4 * (h[t] - l[t]) if dr > 0 else h[t] + 0.4 * (h[t] - l[t]), '^' if dr > 0 else 'v', color=UP if dr > 0 else DN, ms=6)
    ax.set_xlim(x0 - 1, N + 12); ax.set_ylim(l[x0:].min() - 10, h[x0:].max() + 10)
    ax.tick_params(colors='#aaa'); [sp.set_color('#444') for sp in ax.spines.values()]
    ax.set_title(f'XAUUSD {tf} with {htf} (thick lines), last {n} candles to {d.index[-1]} - preview of GoldChannels v1.10 defaults; dashed = live, faded = weak', color='#ddd')
    plt.tight_layout(); plt.savefig(out, dpi=80, facecolor='black')
draw('H1', 400, '../img/preview_H1.png'); draw('M15', 400, '../img/preview_M15.png')
