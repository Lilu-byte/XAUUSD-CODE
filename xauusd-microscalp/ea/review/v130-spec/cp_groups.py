import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-candles/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np
from mlib import Harness
import ea_replica as R
import ea_replica_v130 as V
H = Harness(); m = H.m1; tr = R.h1_trend(m)
t = m.tod.values; ins = (t >= 900) & (t < 1140)
for g in V.PAT_GROUPS:
    a = V.cp_signal(m, tr, (g,), 0.0); b = V.cp_signal(m, tr, (g,), 0.5)
    print(f'{g:10s} in session, with trend: body 0 -> {int((a!=0)[ins].sum()):4d}   body 0.5 -> {int((b!=0)[ins].sum()):4d}')
