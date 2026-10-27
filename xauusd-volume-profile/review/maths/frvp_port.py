# Literal port of Redraw() lines 279-358 of FixedRangeVolumeProfile.mq5 (price grid, volume spread,
# POC, value area, POCpx/VAH/VAL). Same IEEE-double operations in the same order as the MQL5 code.
import math

POINT = 0.01


def RowOf(p, base, step, rows):                       # lines 239-245
    k = int(math.floor((p - base) / step))
    if k < 0: k = 0
    if k > rows - 1: k = rows - 1
    return k


def redraw(highs, lows, opens, closes, vols, InpRows=60, InpRowSize=0.0, InpValueAreaPct=70.0, _Point=POINT):
    n = len(highs)
    # price grid (285-303)
    hi, lo = -1.7976931348623157e308, 1.7976931348623157e308
    for i in range(n):
        if highs[i] > hi: hi = highs[i]
        if lows[i] < lo: lo = lows[i]
    if hi - lo < _Point: hi = lo + _Point
    capped = False
    if InpRowSize > 0:
        step = InpRowSize
        base = math.floor(lo / step) * step
        rows = int(math.ceil((hi - base) / step - 1e-9))
        if rows < 1: rows = 1
        if rows > 2000: rows = 2000; base = lo; step = (hi - lo) / rows; capped = True
    else:
        rows = InpRows
        base = lo
        step = (hi - lo) / rows
    # spread (306-324)
    gUp = [0.0] * rows; gDn = [0.0] * rows; gTot = [0.0] * rows

    def AddVol(k, v, up):
        if up: gUp[k] += v
        else: gDn[k] += v

    for i in range(n):
        v = float(vols[i])
        if v <= 0: continue
        up = closes[i] >= opens[i]
        h, l = highs[i], lows[i]
        a, b = RowOf(l, base, step, rows), RowOf(h, base, step, rows)
        if a == b or h - l < _Point * 0.5:
            AddVol(a, v, up); continue
        for k in range(a, b + 1):
            rl = base + k * step; rh = rl + step
            if k == rows - 1: rh = max(rh, h)
            if k == 0: rl = min(rl, l)
            ov = min(h, rh) - max(l, rl)
            if ov > 0: AddVol(k, v * ov / (h - l), up)
    # POC (327-338)
    s, maxv, mid = 0.0, 0.0, (rows - 1) / 2.0
    poc = 0
    for k in range(rows):
        gTot[k] = gUp[k] + gDn[k]
        s += gTot[k]
        if gTot[k] > maxv * (1 + 1e-12) or (gTot[k] >= maxv * (1 - 1e-12) and gTot[k] > 0 and abs(k - mid) < abs(poc - mid)):
            maxv = gTot[k]; poc = k
    if s <= 0 or maxv <= 0:
        return None
    # value area (347-358)
    target = s * InpValueAreaPct / 100.0
    acc = gTot[poc]
    vaLo = vaHi = poc
    last = gTot[poc]
    while acc < target - s * 1e-12 and (vaLo > 0 or vaHi < rows - 1):
        above = gTot[vaHi + 1] if vaHi < rows - 1 else -1.0
        below = gTot[vaLo - 1] if vaLo > 0 else -1.0
        if above >= below: vaHi += 1; acc += gTot[vaHi]; last = gTot[vaHi]
        else: vaLo -= 1; acc += gTot[vaLo]; last = gTot[vaLo]
    pocPx = base + (poc + 0.5) * step
    vah = base + (vaHi + 1) * step
    val = base + vaLo * step
    return dict(rows=rows, base=base, step=step, hi=hi, lo=lo, up=gUp, dn=gDn, tot=gTot, sum=s, maxv=maxv,
                poc=poc, vaLo=vaLo, vaHi=vaHi, acc=acc, last=last, pocPx=pocPx, vah=vah, val=val, capped=capped)
