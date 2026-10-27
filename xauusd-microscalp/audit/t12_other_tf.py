"""Do the separate M5/M15/H1/H4/D1 files line up with bars resampled from the M1 file (same clock, same labels)?"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd, mlib
m1 = mlib.load_m1()
for tf in ('M5', 'M15', 'H1', 'H4', 'D1'):
    f = mlib.load(tf)
    r = mlib.resample(m1, mlib.MIN[tf])
    common = f.index.intersection(r.index)
    common = common[(common > m1.index[0] + pd.Timedelta(days=1)) & (common < m1.index[-1] - pd.Timedelta(days=1))]
    best = None
    for sh in (-120, -60, 0, 60, 120):
        rs = r.copy(); rs.index = rs.index + pd.Timedelta(minutes=sh)
        cm = f.index.intersection(rs.index); cm = cm[(cm > m1.index[0] + pd.Timedelta(days=1)) & (cm < m1.index[-1] - pd.Timedelta(days=1))]
        if len(cm) == 0: continue
        err = (f.loc[cm, 'close'] - rs.loc[cm, 'close']).abs().median()
        if best is None or err < best[1]: best = (sh, err, len(cm))
    e0 = (f.loc[common, ['open', 'high', 'low', 'close']] - r.loc[common, ['open', 'high', 'low', 'close']]).abs()
    print(f'{tf}: file {f.index[0]}..{f.index[-1]} ({len(f)} bars); overlap {len(common)}; median |diff| O/H/L/C at shift 0: '
          f'{e0.median().round(3).tolist()}; exact close match {(e0.close < 0.005).mean():.3f}; best shift {best}')
