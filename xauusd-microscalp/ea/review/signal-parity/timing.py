"""Entry at signal-bar close (harness) vs next-bar open (EA). Same signals, defaults, FAIR fills, base spread."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea/review/signal-parity')
import ea_replica as R
from mlib import Harness, summarize, FILL
from sim_next import _sim_next

H = Harness(); m = H.m1; tr = R.h1_trend(m)
S = {'PB': R.sig_pullback(m, tr), 'SF': R.sig_spike_fade(m), 'QB': R.sig_quarter_fade(m), 'CP': R.sig_patterns(m, tr)}
rows = []
for k, s in S.items():
    tp, sl, to, mo = R.DEFAULTS[k]
    d0, t0 = H.run(s, tp, sl, timeout=to, max_open=mo)
    sg = np.sign(np.nan_to_num(np.asarray(s, float))).astype(np.int64)
    dp, dt, ti, tox, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, H._spr['base'], H.tod, H.day, H.last, sg, float(tp), float(sl), int(to), int(mo), FILL['FAIR'], 0.0, 0.0, 0)
    d1 = pd.DataFrame({'pnl': dp, 'trades': dt}, index=H.dates)
    t1 = pd.DataFrame({'entry': m.index[ti], 'dir': tdr, 'pnl': tpn})
    for per in ('train', 'test'):
        a, b = summarize(d0, t0, per), summarize(d1, t1, per)
        rows.append(dict(module=k, period=per, close_entry_day=a['per_day'], next_open_day=b['per_day'], diff_day=b['per_day'] - a['per_day'],
                         close_entry_trade=a['per_trade'], next_open_trade=b['per_trade'], trades=len(t0), trades_next=len(t1)))
print(pd.DataFrame(rows).round(4).to_string(index=False))
