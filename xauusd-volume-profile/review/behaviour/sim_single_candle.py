# Replays Redraw() lines 285-338 and 361-378 of FixedRangeVolumeProfile.mq5 in IEEE doubles
# for a single source candle (the range is one candle and the source TF equals the chart TF).
import math, random, sys

def rowof(p, base, step, rows):
    k = int(math.floor((p - base) / step))
    return max(0, min(rows - 1, k))

def profile(lo, hi, v, rows=60, point=0.01):
    if hi - lo < point: hi = lo + point
    base, step = lo, (hi - lo) / rows
    up = [0.0] * rows
    a, b = rowof(lo, base, step, rows), rowof(hi, base, step, rows)
    for k in range(a, b + 1):
        rl = base + k * step; rh = rl + step
        if k == rows - 1: rh = max(rh, hi)
        if k == 0: rl = min(rl, lo)
        ov = min(hi, rh) - max(lo, rl)
        if ov > 0: up[k] += v * ov / (hi - lo)
    maxv, poc, mid = 0.0, 0, (rows - 1) / 2.0
    for k in range(rows):
        t = up[k]
        if t > maxv * (1 + 1e-12) or (t >= maxv * (1 - 1e-12) and t > 0 and abs(k - mid) < abs(poc - mid)):
            maxv, poc = t, k
    spread = (max(up) - min(up)) / max(up)
    return poc, spread

random.seed(1)
pocs = []
for _ in range(2000):
    lo = round(random.uniform(1800, 4200), 2)
    hi = round(lo + random.uniform(0.3, 15), 2)
    v = random.randint(20, 3000)
    poc, spread = profile(lo, hi, v)
    pocs.append(poc)
far = sum(1 for p in pocs if abs(p - 29.5) > 5)
print("single candle, 60 rows: POC row distribution (ideal = 29 every time)")
print("  POC == 29:", sum(1 for p in pocs if p == 29), "/", len(pocs))
print("  POC more than 5 rows from the middle:", far, "/", len(pocs))
print("  example POCs:", pocs[:20])
lo, hi = 2650.12, 2651.47
print("  example candle", lo, hi, "-> POC row", profile(lo, hi, 500)[0], "relative row spread", profile(lo, hi, 500)[1])

# Row widths in chart candles (line 362: maxW = nb * InpWidthPct/100), and what MT5 can show
# if it places a time between two bar opens at the bar holding it (whole-candle widths).
print()
print("longest row, in candles, for InpWidthPct = 30:")
for nb in (1, 2, 3, 5, 10, 20, 121):
    maxW = nb * 30 / 100.0
    print(f"  nb={nb:4d}: maxW={maxW:6.2f} candles -> longest row drawn {math.floor(maxW)} whole candles; "
          f"rows under {min(1.0, 1/maxW)*100:5.1f}% of the POC have zero drawn width (left placement)")
