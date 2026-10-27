"""TRAIN only: does simply trading WITH the HTF trend at every bar already have the edge? (baseline for
the 'fade counter-trend strong candle' theme found in edge_halves.py)."""
from pats import *
H = Harness(); m = H.m1
ok = m.tod.values < END_TOD - 15
A = ok & (m.index < pd.Timestamp('2026-08-01')); B = ok & (m.index >= pd.Timestamp('2026-08-01')) & (m.index < SPLIT)
spr = spread_series(m, 'base'); HZ = (1, 2, 3, 5, 10)
FWD = {k: (m.close.shift(-k) - m.close).values for k in HZ}
def row(sig, lab):
    out = [lab]
    for msk in (A, B):
        mm = msk & (sig != 0)
        out += [round(np.nanmean(FWD[k][mm] * sig[mm]), 3) for k in HZ]
    print(out)
print('label, A: m1 m2 m3 m5 m10, B: m1 m2 m3 m5 m10 (gross move, before spread)')
for tf in ('M15', 'H1'):
    t = trend(m, tf); row(t, f'always with {tf} trend')
# M1 last-candle direction fade/follow (simplest reversal test)
d1 = np.sign(m.close - m.open).values
row(d1, 'follow last M1 candle colour'); row(-d1, 'fade last M1 candle colour')
t = trend(m, 'M15')
row(np.where(d1 == -t, t, 0), 'M1 candle against M15 trend -> enter with trend')
