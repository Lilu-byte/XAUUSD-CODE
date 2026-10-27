import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-candles/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import numpy as np, pandas as pd
from mlib import Harness, resample
import ea_replica as R
import ea_replica_v130 as V
H = Harness(); m = H.m1; tr = R.h1_trend(m)
c = resample(m, 2)
body = (c.close - c.open).abs(); rng = c.high - c.low
avg = body.shift(1).rolling(20).mean(); avgr = rng.shift(1).rolling(20).mean()
hit = (body >= avg) & (body >= 0.9 * rng) & (rng > 0)
tod = c.index.hour * 60 + c.index.minute + 1          # signal M1 bar = last minute of the 2-min candle
ins = (tod >= 900) & (tod < 1140)
x = (body / avgr)[hit & ins]
print('PB raw hits in session (before trend):', len(x))
print('body / avg range quantiles:', x.quantile([0, .01, .05, .1, .25, .5]).round(3).to_dict())
for b in (0.5, 0.6, 0.7, 0.8, 1.0):
    print(f'  min body {b}: removes {(x < b).mean():.1%}')
# how many removed by min-body 0.5 also pass the trend and session (the EA-level PB signal)
for b in (0.5, 0.8, 1.0):
    s0 = V.pb_signal(m, tr, body_min=0.0); s1 = V.pb_signal(m, tr, body_min=b)
    mt = m.tod.values; i2 = (mt >= 900) & (mt < 1140)
    print(f'EA-level PB in session: body 0 -> {int((s0!=0)[i2].sum())}, body {b} -> {int((s1!=0)[i2].sum())}')
