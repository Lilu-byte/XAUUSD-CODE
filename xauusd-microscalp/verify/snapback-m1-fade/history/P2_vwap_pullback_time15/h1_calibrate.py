"""Scale calibration for the ports (no P&L is looked at here): how the M1 threshold 2.5 x ATR240(M1) on a 3-bar move
translates to a 1-bar move on M5 / M15 bars, measured on the overlap period (M1 file dates)."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *
m1 = load_tf('M1'); A1 = Arr(m1)
F1 = A1.feats(3, 240)
thr1 = 2.5 * F1['atr']
print(f'M1: mean ATR240 {np.nanmean(F1["atr"]):.3f}; threshold 2.5xATR mean ${np.nanmean(thr1):.2f}; sd(r3) {np.nanstd(F1["r"]):.3f}; '
      f'z of threshold (thr/sd r3) {np.nanmean(thr1) / np.nanstd(F1["r"]):.2f}; share of bars |r3|>thr {np.nanmean(np.abs(F1["r"]) > thr1):.4f}')
for tf, natr in (('M5', 48), ('M15', 16)):
    m = load_tf(tf); A = Arr(m, tf)
    print(f'{tf}: {m.index[0]} .. {m.index[-1]}, {len(m)} bars; tod range {m.tod.min()}-{m.tod.max()}; '
          f'days {len(A.dates)}; recorded spread median {np.median(A.rec):.3f} (zero share raw {(m.spread <= 0).mean():.2f})')
    F = A.feats(1, natr)
    ov = (m.index >= M1START)
    atr_ov = np.nanmean(F['atr'][ov]); sd_ov = np.nanstd(F['r'][ov])
    ratio = np.nanmean(F1['atr']) / atr_ov
    k_usd = 2.5 * ratio                                  # same dollar threshold as the M1 rule
    z1 = np.nanmean(thr1) / np.nanstd(F1['r'])
    k_z = z1 * sd_ov / atr_ov                            # same standardized size of move (z) on a 1-bar move
    # share of bars firing at each k (overlap period) and per day
    nd = len(np.unique(m.index[ov].date))
    msg = ', '.join(f'k{k:.2f}: {np.nansum(np.abs(F["r"][ov]) > k * F["atr"][ov]) / nd:.1f}/day' for k in (k_usd, k_z, 1.0, 1.5, 2.0, 2.5))
    print(f'   overlap mean ATR{natr} {atr_ov:.3f}, sd(r1) {sd_ov:.3f}, ATR_M1/ATR_{tf} {ratio:.3f} -> dollar-matched k {k_usd:.2f}, '
          f'z-matched k {k_z:.2f}; raw-move bars/day: {msg}')
    for nm, a, b in (('2022-07..2025-05', '2022-07-01', '2025-05-05'), ('2025-05..2026-06', '2025-05-05', '2026-06-26'), ('M1 period', '2026-06-26', '2026-10-10')):
        sel = (m.index >= a) & (m.index < b)
        if sel.sum() == 0: continue
        print(f'   {nm}: mean ATR{natr} {np.nanmean(F["atr"][sel]):.2f}, mean price {m.close[sel].mean():.0f}, median recorded spread {np.median(A.rec[sel]):.2f}')
# M1 signal frequency
s = A1.signal(); nd1 = len(A1.dates)
print(f'M1 P2 raw signal bars/day {np.sum(s != 0) / nd1:.1f}; with gate off {np.sum(A1.signal(gate="none", sgate=0) != 0) / nd1:.1f}')
