"""(1d) Bridge: on the M1 period, does the M5 port trade the same days as the M1 rule? Daily P&L correlation between
the M1 pick and the M5 / M15 ports (the M5 file equals M1 resampled to 5 minutes on the overlap: 20,002 bars, all OHLCV identical)."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *
m = load_tf('M1'); A = Arr(m); d1, _ = A.run(A.signal())
for tf, natr, hold, k in (('M5', 48, 3, 1.05), ('M5', 48, 3, 1.35), ('M15', 16, 1, 1.30), ('M15', 16, 1, 0.59)):
    mm = load_tf(tf); B = Arr(mm, tf); dB, _ = B.run(B.signal(k=k, L=1, atr_n=natr), sl=25.0, hold=hold, mo=3, spr=0.20)
    j = pd.concat([d1.pnl.rename('m1'), dB.pnl.rename('p')], axis=1, join='inner')
    print(f'{tf} k {k:.2f}: daily P&L correlation with the M1 pick on the {len(j)} M1-period days: {j.corr().iloc[0, 1]:+.2f} '
          f'(TRAIN dates {j[j.index < SPLIT].corr().iloc[0, 1]:+.2f}, TEST dates {j[j.index >= SPLIT].corr().iloc[0, 1]:+.2f})')
