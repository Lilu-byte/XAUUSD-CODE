# Value-area checks on real M1 ranges: other percentages, and how often the greedy step meets a tie.
import sys
import numpy as np
sys.path.insert(0, '/mnt/project-files/xauusd-volume-profile/review/maths')
from common import sel
from frvp_port import redraw
import frvp_ref as ref

RANGES = [('2026-10-02 16:00', '2026-10-02 16:59'), ('2026-10-08 00:00', '2026-10-08 23:59'), ('2026-09-28 00:00', '2026-10-02 23:59'),
          ('2026-09-01 00:00', '2026-09-30 23:59'), ('2026-07-01 00:00', '2026-07-01 23:59')]
bad = 0; n = 0; worst_over = 0
for t0, t1 in RANGES:
    d = sel('M1', t0, t1)
    for c in (dict(InpRows=60), dict(InpRowSize=0.5), dict(InpRowSize=1.0)):
        for pct in (1.0, 30.0, 50.0, 68.0, 70.0, 80.0, 95.0, 99.0, 100.0):
            p = redraw(d['high'].tolist(), d['low'].tolist(), d['open'].tolist(), d['close'].tolist(), d['tick_volume'].tolist(), InpValueAreaPct=pct, **c)
            r = ref.poc_va(np.array(p['tot']), pct)
            sh = p['acc'] / p['sum'] * 100
            ok = sh >= pct - 1e-9 and ((p['acc'] - p['last']) / p['sum'] * 100 < pct or p['vaLo'] == p['vaHi']) and (p['vaLo'], p['vaHi']) == (r['vaLo'], r['vaHi'])
            n += 1; bad += (not ok); worst_over = max(worst_over, sh - pct)
            if pct == 100.0 and not (p['vaLo'] == 0 and p['vaHi'] == p['rows'] - 1):
                # 100%: the VA must run to the outermost non-zero rows
                nz = np.nonzero(np.array(p['tot']) > 0)[0]
                if not (p['vaLo'] <= nz[0] and p['vaHi'] >= nz[-1]): bad += 1
print(f"value area at 1..100%: {n} profiles, failures (share < pct, last row unneeded, or port != independent greedy) {bad}")

# ties met by the greedy step (above vs below within 1e-9 of each other, both > 0) in real profiles
ties = steps = 0
for t0, t1 in RANGES + [('2026-07-01 00:00', '2026-07-31 23:59'), ('2026-08-10 00:00', '2026-08-14 23:59')]:
    d = sel('M1', t0, t1)
    for c in (dict(InpRows=24), dict(InpRows=60), dict(InpRows=120), dict(InpRowSize=0.5), dict(InpRowSize=1.0), dict(InpRowSize=5.0)):
        p = redraw(d['high'].tolist(), d['low'].tolist(), d['open'].tolist(), d['close'].tolist(), d['tick_volume'].tolist(), **c)
        t = p['tot']; lo = hi = p['poc']; acc = t[lo]; s = p['sum']
        while acc < s * 0.7 - s * 1e-12 and (lo > 0 or hi < p['rows'] - 1):
            a = t[hi + 1] if hi < p['rows'] - 1 else -1.0; b = t[lo - 1] if lo > 0 else -1.0
            steps += 1
            if a > 0 and b > 0 and abs(a - b) <= 1e-9 * max(a, b): ties += 1
            if a >= b: hi += 1; acc += t[hi]
            else: lo -= 1; acc += t[lo]
print(f"greedy steps on real M1 profiles: {steps}; steps where the two candidate rows tie within 1e-9: {ties}")
