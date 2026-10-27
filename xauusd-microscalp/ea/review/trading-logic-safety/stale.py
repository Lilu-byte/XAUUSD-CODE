import sys; sys.path.insert(0,'/mnt/project-files/xauusd-microscalp/code'); sys.path.insert(0,'/mnt/project-files/xauusd-microscalp/ea')
from mlib import *
import ea_replica as R
m = load_m1(); tr = R.h1_trend(m)
S = {'PB': R.sig_pullback(m, tr), 'SF': R.sig_spike_fade(m), 'QB': R.sig_quarter_fade(m), 'CP': R.sig_patterns(m, tr)}
idx = m.index
nxt = idx.to_series().shift(-1)
gapnext = (nxt - idx.to_series()).dt.total_seconds().values / 60
tod = m.tod.values
win = (tod >= 65) & (tod <= 22*60+29)
cand = np.where(win & ((gapnext > 1.5) | np.isnan(gapnext)))[0]
for i in cand:
    s = {k: int(v[i]) for k, v in S.items() if v[i] != 0}
    print(idx[i], 'next bar after', gapnext[i], 'min', 'last_of_session' if m.last_of_session.values[i] else '', 'signals', s)
# how many signal bars are in the window and followed by a gap at all
