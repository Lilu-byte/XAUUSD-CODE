"""Fixed indicator TrendAt emulation; spread filter and daily-loss halt not modelled by the replica."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
import ea_replica as R
from mlib import load_m1, load, ema, Harness
m = load_m1(); tr = R.h1_trend(m)
h1 = load('H1'); h1v = np.sign(ema(h1.close, 20) - ema(h1.close, 80)).values
h1t = h1.index.values.astype('datetime64[s]').astype(np.int64)
Tc = m.index.values.astype('datetime64[s]').astype(np.int64)
t = Tc + 60
sh = np.searchsorted(h1t, t - 1, 'right') - 1                 # iBarShift(H1, t - 1, false)
sh = np.where(h1t[sh] + 3600 > t, sh - 1, sh)                 # still forming at t -> older bar
fixed = np.where(sh >= 0, h1v[np.clip(sh, 0, None)], 0)
print('fixed TrendAt == replica trend on', (fixed == tr).mean(), 'of bars; differing', (fixed != tr).sum())
# spread filter InpMaxSpreadPts = 50 (recorded M1 spread is the bar minimum, so this undercounts)
S = {'PB': R.sig_pullback(m, tr), 'SF': R.sig_spike_fade(m), 'QB': R.sig_quarter_fade(m)}
win = (m.tod.values >= 65) & (m.tod.values <= 1349) & ~m.last_of_session.values
for k, s in S.items():
    x = (np.nan_to_num(s) != 0) & win
    print(k, 'tradable signals', x.sum(), 'with recorded spread > 50 pts:', (x & (m.spread.values > 50)).sum())
H = Harness(m)
dd = {}
for k, s in S.items():
    tp, sl, to, mo = R.DEFAULTS[k]; d, _ = H.run(s, tp, sl, timeout=to, max_open=mo); dd[k] = d.pnl
p = pd.DataFrame(dd).sum(axis=1)
print('PB+SF+QB days with closed P&L <= -15 (EA would halt that day):', (p <= -15).sum(), 'of', len(p), 'worst', p.min().round(1))
