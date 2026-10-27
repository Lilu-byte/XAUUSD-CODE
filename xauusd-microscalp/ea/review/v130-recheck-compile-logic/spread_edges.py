"""Emulate EA SpreadVeto and indicator SpreadTooWide in IEEE doubles over many prices.
Quotes are the doubles nearest to decimal prices (as MT5 stores normalized prices)."""
import numpy as np
def run(digits, pcts=(50, 40, 30, 60), tps=(0.25, 0.15, 0.20, 0.30, 0.10), maxpts=50):
    pt = 10.0 ** -digits
    scale = 10 ** digits
    ticks = np.arange(1500 * scale, 4500 * scale, 7 if digits == 2 else 61, dtype=np.int64)   # bid in integer points
    bid = ticks / scale                                                                       # nearest double to the decimal
    bad = 0
    for pct in pcts:
        for tp in tps:
            lim = pct / 100.0 * tp
            exact_lim_pts = pct * tp * scale / 100                                            # exact decimal limit in points
            for n in range(0, 200 if digits == 2 else 600):
                ask = (ticks + n) / scale
                spr = ask - bid
                pts = np.round(spr / pt).astype(np.int64)
                ea_pct_veto = spr > lim + pt * 0.001
                ind_pct_veto = (n * pt) > lim + pt * 0.001                                     # indicator history: spread[i-1]*_Point
                want = n > exact_lim_pts + 1e-9
                if (ea_pct_veto != want).any() or (ind_pct_veto != want):
                    bad += 1; print('MISMATCH pct', digits, pct, tp, n, ea_pct_veto.sum(), want)
                if (pts != n).any():
                    bad += 1; print('POINTS MISMATCH', digits, n)
    return bad
for d in (2, 3):
    print('digits', d, 'mismatches:', run(d))
# the two cases the task names, 2 digits
pt = 0.01
for pct, tp, n in ((50, 0.25, 12), (50, 0.25, 13), (40, 0.25, 10), (40, 0.25, 11)):
    lim = pct / 100.0 * tp
    worst_hi = max((round(b + n * pt, 2) - b) for b in np.round(np.arange(1500, 4500, 0.37), 2))
    print(f'{pct}% of {tp}: lim={lim!r}  {n} points: max ask-bid {worst_hi!r} -> {"VETO" if worst_hi > lim + pt * 0.001 else "pass"}')
