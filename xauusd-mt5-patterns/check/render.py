import sys, pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
csv, n1, bars, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
title = sys.argv[5] if len(sys.argv) > 5 else ''
df = pd.read_csv(csv).iloc[:n1 - 1]
lo_i = n1 - 1 - bars
d = df.iloc[lo_i:]
def col(c): c = int(c); return ((c & 255) / 255, ((c >> 8) & 255) / 255, ((c >> 16) & 255) / 255)
W, H, DPI = 15, 7.5, 110
fig, ax = plt.subplots(figsize=(W, H), dpi=DPI); fig.patch.set_facecolor('black'); ax.set_facecolor('black')
for i, r in zip(range(lo_i, n1 - 1), d.itertuples()):
    up = r.close >= r.open
    ax.plot([i, i], [r.low, r.high], color='#9a9a9a', lw=0.6, zorder=2)
    ax.add_patch(Rectangle((i - 0.35, min(r.open, r.close)), 0.7, max(abs(r.close - r.open), 0.01), color=('black' if up else '#9a9a9a'), ec='#9a9a9a', lw=0.6, zorder=3))
X = lambda t: (int(t) - 1000000) // 3600
ls = {0: '-', 1: '--', 2: ':'}
ymin, ymax = d.low.min(), d.high.max(); pad = (ymax - ymin) * 0.08
ax.set_xlim(lo_i - 2, n1 + 45); ax.set_ylim(ymin - pad, ymax + pad * 2.2); ax.set_xticks([]); fig.subplots_adjust(left=0.01, right=0.95, top=0.98, bottom=0.02); fig.canvas.draw(); bb = ax.get_window_extent(); AW, AH = bb.width, bb.height
def px(xd, yd, corner, w=0, h=0):   # pixel offsets from a corner -> axes fraction of the upper-left point
    x = xd if corner in (0, 1) else AW - xd
    y = yd if corner in (0, 3) else AH - yd
    return x / AW, 1 - y / AH
for line in open('objs.tsv'):
    f = line.rstrip('\n').split('\t'); nm, ty = f[0], int(f[1]); t1, p1, t2, p2 = X(f[2]), float(f[3]), X(f[4]), float(f[5])
    c, st, w, fill, anc, yd, fs, txt = col(f[6]), int(f[7]), int(f[8]), int(f[9]), int(f[10]), int(f[11]), int(f[12]), f[13]
    corner, xd, xs, ys, bgc = int(f[14]), int(f[15]), int(f[16]), int(f[17]), col(f[18])
    if ty == 21:
        fx, fy = px(xd, yd, corner)
        ax.add_patch(Rectangle((fx, fy - ys / AH), xs / AW, ys / AH, transform=ax.transAxes, fc=bgc, ec=c, lw=0.8, zorder=8, clip_on=True)); continue
    if ty == 14:
        fx, fy = px(xd, yd, corner)
        va = 'bottom' if anc in (2, 3, 4) else 'top'; ha = 'right' if anc in (4, 5, 6) else 'left'
        ax.text(fx, fy, txt, transform=ax.transAxes, color=c, fontsize=9, va=va, ha=ha, zorder=9, clip_on=True); continue
    if max(t1, t2) < lo_i: continue
    if ty == 2: ax.plot([t1, t2], [p1, p2], color=c, lw=w * 0.9, ls=ls.get(st, '-'), zorder=5)
    elif ty == 10: ax.add_patch(Rectangle((t1, min(p1, p2)), t2 - t1, abs(p2 - p1), fc=c if fill else 'none', ec=c, ls=ls.get(st, '-'), lw=0.8, zorder=1))
    elif ty == 13:
        va = {3: 'bottom', 7: 'top', 1: 'center', 0: 'top', 2: 'bottom'}.get(anc, 'center'); ha = 'left' if anc in (0, 1, 2) else 'center'
        ax.text(t1, p1, txt, color=c, fontsize=7 if fs <= 8 else 8, va=va, ha=ha, zorder=7)
    elif ty in (100, 101): ax.plot([t1], [p1 - pad * 0.15 if ty == 100 else p1 + pad * 0.15], marker='^' if ty == 100 else 'v', color=c, ms=8, zorder=6)
    elif ty == 102: ax.text(t1, p1, '✔', color=c, fontsize=10, ha='center', va='bottom', zorder=7)
    elif ty == 103: ax.text(t1, p1, '✖', color=c, fontsize=9, ha='center', va='bottom', zorder=7)
ax.set_xlim(lo_i - 2, n1 + 45); ax.set_ylim(ymin - pad, ymax + pad * 2.2)
ax.tick_params(colors='#888'); [s.set_color('#444') for s in ax.spines.values()]; ax.yaxis.tick_right(); ax.set_xticks([])
if title: ax.set_title(title, color='#aaa', fontsize=10, loc='left')
plt.savefig(out, facecolor='black')
