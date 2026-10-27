"""Edge scan (TRAIN only) of single-condition momentum / mean-reversion signals. Direction = FOLLOW
(the sign of the move just seen); a negative move means fading it would earn that amount."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from scan_lib import *
import time
t0 = time.time()
H = Harness(); m = H.m1; f = build(m); S = Scanner(m, f)
sg = lambda x: np.sign(np.nan_to_num(x))
# 1) last k-bar return sign, by size ($) and by size in ATR units
for k in (1, 2, 3, 5):
    r = f[f'r{k}'].values
    S.add(f'r{k}_any', sg(r))
    for th in (0.5, 1, 2, 3, 4, 6):
        S.add(f'r{k}>{th}$', np.where(np.abs(r) > th, sg(r), 0))
    ra = r / f.atr20.values
    for th in (1, 1.5, 2, 3):
        S.add(f'r{k}>{th}atr', np.where(np.abs(ra) > th, sg(r), 0))
# body sign
S.add('body_any', sg(f.body.values))
# 2) streaks
st = f.streak.values
for n in (2, 3, 4, 5, 6, 7):
    S.add(f'streak=={n}', np.where(np.abs(st) == n, sg(st), 0))
    S.add(f'streak>={n}', np.where(np.abs(st) >= n, sg(st), 0))
# 3) RSI extremes (follow = high RSI -> +1)
for n in (2, 3, 7):
    x = f[f'rsi{n}'].values
    for lo in (2, 5, 10, 20, 30):
        S.add(f'rsi{n}_ext{lo}', np.where(x > 100 - lo, 1, np.where(x < lo, -1, 0)))
# 4) z-score extremes, Bollinger touches
for n in (10, 20, 30, 60):
    z = f[f'z{n}'].values
    for th in (1.5, 2, 2.5, 3):
        S.add(f'z{n}>{th}', np.where(z > th, 1, np.where(z < -th, -1, 0)))
    bu = f[f'bbu{n}'].values > 0; bl = f[f'bbl{n}'].values > 0
    S.add(f'bb{n}_touch', np.where(bu & ~bl, 1, np.where(bl & ~bu, -1, 0)))
    zc = z
    S.add(f'bb{n}_reject', np.where(bu & (zc < 2), 1, np.where(bl & (zc > -2), -1, 0)))  # pierced but closed inside
# 5) VWAP distance
vd = f.vw_d.values; vda = f.vw_da.values
for th in (2, 4, 6, 10, 15):
    S.add(f'vwap>{th}$', np.where(np.abs(vd) > th, sg(vd), 0))
for th in (2, 4, 6, 10):
    S.add(f'vwap>{th}atr', np.where(np.abs(vda) > th, sg(vd), 0))
# 6) tick-volume spikes with candle direction
vr = f.vrel.values; b = sg(f.body.values)
for th in (1.5, 2, 3, 4, 6):
    S.add(f'vspike>{th}', np.where(vr > th, b, 0))
    S.add(f'vquiet<{1/th:.2f}', np.where(vr < 1 / th, b, 0))
# 7) range-expansion bars
rx = f.rexp.values
for th in (1.5, 2, 2.5, 3, 4):
    S.add(f'rexp>{th}', np.where(rx > th, b, 0))
    S.add(f'rexp>{th}_strongclose', np.where((rx > th) & ((f.cloc.values > .8) | (f.cloc.values < .2)), b, 0))
# 8) inside-bar breakouts
S.add('ib_break_mother', np.where(f.ib_up.values, 1, np.where(f.ib_dn.values, -1, 0)))
S.add('ib_break_inside', np.where(f.ib_up2.values, 1, np.where(f.ib_dn2.values, -1, 0)))
# 9) close location (close near high = bullish)
cl = f.cloc.values
for th in (0.1, 0.2):
    S.add(f'cloc_ext{th}', np.where(cl > 1 - th, 1, np.where(cl < th, -1, 0)))
t = S.table()
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
cols = ['nT', 'sprT', 'm1T', 'm2T', 'm3T', 'm5T', 'm10T', 't3', 'bestk', 'net', 'dir', 'netA', 'netB', 'A_B_same']
t.to_csv('scan1_train.csv')
print(t[cols].sort_values('net', ascending=False).head(40).round(3))
print('\nn signals tested:', len(t), 'positive train net:', (t.net > 0).sum(), ' positive in both A and B:', ((t.netA > 0) & (t.netB > 0)).sum())
print('time', time.time() - t0)
