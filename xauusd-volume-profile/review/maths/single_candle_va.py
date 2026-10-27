# Single-candle range, 60 rows: value area placement with the code's rule (above >= below goes up),
# (a) as the code computes the rows, (b) with exactly equal rows (overlaps in row units).
import sys, random
from collections import Counter
sys.path.insert(0, '/mnt/project-files/xauusd-volume-profile/review/maths')
from frvp_port import redraw

def va(t, poc, rows=60):
    s = sum(t); lo = hi = poc; acc = t[poc]
    while acc < s * 0.7 - s * 1e-12 and (lo > 0 or hi < rows - 1):
        a = t[hi + 1] if hi < rows - 1 else -1.0; b = t[lo - 1] if lo > 0 else -1.0
        if a >= b: hi += 1; acc += t[hi]
        else: lo -= 1; acc += t[lo]
    return lo, hi
random.seed(11); code = Counter()
for _ in range(2000):
    lo = round(random.uniform(1800, 4200), 2); hi = round(lo + random.uniform(0.3, 15), 2)
    p = redraw([hi], [lo], [lo], [hi], [500], InpRows=60)
    code[(p['vaLo'], p['vaHi'])] += 1
print("code as written, VA rows (lo, hi) -> count, top 8:", code.most_common(8))
print("exactly equal rows, POC row 29:", va([500 / 60] * 60, 29), "(VAL..VAH in rows; centred would be about 8..49 or 9..50)")
lo, hi = 4100.00, 4106.00
p = redraw([hi], [lo], [lo], [hi], [600], InpRows=60)
print(f"example candle {lo}-{hi}: POC {p['pocPx']:.2f}, VAL {p['val']:.2f}, VAH {p['vah']:.2f} (a centred 70% would be about 4100.90-4105.10)")
