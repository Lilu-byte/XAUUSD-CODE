"""TRAIN-only diagnostic: is the VWAP-'toward' fade a snap-back, or just 'trade to the session-VWAP side'
(intraday trend following)? Compare the toward-gated fade with the VWAP-side direction on (a) the same bars,
(b) random bars with the same count, (c) every bar, and (d) the toward gate with no size threshold."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from sb import *
m, H = load_train(); f = feats(m)
side = np.sign(f.vw_d.values)
rng = np.random.default_rng(0)
def show(name, s, N=15, sl=25.0, mo=5):
    d, t = H.run_x(s, (1000.0,), sl, N, mo, 0); r = halves(d, t)
    print(f'{name:58s} N{N:>2} mo{mo}: {r["pd_tr"]:+7.2f}/day (A {r["pd_A"]:+6.2f} B {r["pd_B"]:+6.2f}) {r["tpd_tr"]:5.1f} tr/day '
          f'{r["pt_tr"]:+.3f}/tr win {r["win_tr"]:.2f} long {r["ls_tr"]:.2f} worst day {r["wd_tr"]:+.0f} DD {r["dd_tr"]:+.0f}')
for (k, mode, th) in ((3, 'atr', 2.5), (3, 'atr', 3.0), (3, 'usd', 4.0)):
    for N, mo in ((15, 5), (10, 3), (15, 1)):
        s = fade_signal(f, k, mode, th, 'toward')
        show(f'toward fade k{k} {mode} {th}', s, N, 25.0, mo)
        same_side = np.where(s != 0, side, 0); assert (same_side == s).all()
        nz = (s != 0).mean()
        rb = np.where(rng.random(len(s)) < nz, side, 0)
        show('   VWAP side on random bars, same rate', rb, N, 25.0, mo)
        show('   random direction on the same bars (seed 0)', random_like(s, 0), N, 25.0, mo)
show('VWAP side on EVERY bar', side, 15, 25.0, 5)
show('VWAP side on EVERY bar', side, 15, 25.0, 1)
show('toward gate, any 3-bar move toward VWAP (th 0)', fade_signal(f, 3, 'usd', 0.0, 'toward'), 15, 25.0, 5)
show('snap: k3 atr 3.5 no gate', fade_signal(f, 3, 'atr', 3.5), 3, 15.0, 2)
s = fade_signal(f, 3, 'atr', 3.5); nz = (s != 0).mean()
show('   VWAP side on random bars, same rate', np.where(rng.random(len(s)) < nz, side, 0), 3, 15.0, 2)
show('   snap split: only fades TO the VWAP side', np.where(s == side, s, 0), 3, 15.0, 2)
show('   snap split: only fades AGAINST the VWAP side', np.where(s == -side, s, 0), 3, 15.0, 2)
