"""(4) Look-ahead truncation test: recompute the signal on data cut right after bar i and compare with the full-data
value at bar i. 400 random bars (200 drawn from signal bars, 200 from all bars), plus the ATR/VWAP/r3 values."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/repro/P2_vwap_pullback_time15')
from p2lib import *
m = load_m1()
raw, atr, vw, r3 = signal_df(m)
rng = np.random.default_rng(7)
sigbars = np.flatnonzero(raw != 0)
idx = np.r_[rng.choice(sigbars, 200, replace=False), rng.choice(np.arange(300, len(m)), 200, replace=False)]
mis_sig = mis_val = 0
for i in idx:
    mt = m.iloc[:i + 1]
    s2, a2, v2, r2 = signal_df(mt)
    mis_sig += int(s2[i] != raw[i])
    mis_val += int(not (np.isclose(a2[i], atr[i]) and np.isclose(v2[i], vw[i]) and np.isclose(r2[i], r3[i])))
print(f'truncation test on {len(idx)} bars ({int((raw[idx] != 0).sum())} signal bars): signal mismatches {mis_sig}, '
      f'ATR/VWAP/r3 mismatches {mis_val}')
# the shared loader fills zero recorded spreads with full-sample hour medians (TRAIN only: late Jun-early Jul)
z = (m.spread.values <= 0)
print('signal bars on zero-recorded-spread bars: TRAIN', int(((raw != 0) & z & (m.index < SPLIT)).sum()),
      'TEST', int(((raw != 0) & z & (m.index >= SPLIT)).sum()))
