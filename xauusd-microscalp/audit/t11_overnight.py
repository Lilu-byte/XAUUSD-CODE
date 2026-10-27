"""Positions open at the last bar of a session (22:59) are carried over the break and closed at the next
session's first open (polluted by the reopen spread). Directional size and effect on daily stats."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd, mlib
m1 = mlib.load_m1(); H = mlib.Harness(m1); n = len(m1)
for name, sig in (('all long', np.ones(n)), ('all short', -np.ones(n)),
                  ('coin flip', np.where(np.random.default_rng(1).random(n) < .5, 1, -1))):
    d, tr = H.run(sig, 0.5, 0.5, timeout=10, fill='FAIR', spread='base')
    ii = m1.index.get_indexer(tr.entry); io = ii + tr.bars.values
    xd = H.day[io] != H.day[ii]
    dd = d.copy()
    carried = tr[xd].groupby(tr.entry[xd].dt.normalize()).pnl.sum()
    dd['carried'] = carried.reindex(dd.index).fillna(0)
    print(f'{name:10s}: carried trades {xd.sum()} (of {len(tr)}), mean pnl carried {tr.pnl[xd].mean():+.2f}, '
          f'sum carried {tr.pnl[xd].sum():+.1f} vs sum same-day {tr.pnl[~xd].sum():+.1f}; '
          f'days>=5 with/without carried: {(dd.pnl >= 4.99).mean():.2f}/{((dd.pnl - dd.carried) >= 4.99).mean():.2f}; '
          f'std day pnl with/without: {dd.pnl.std():.2f}/{(dd.pnl - dd.carried).std():.2f}')
# what a sparse signal sees: signal only in last 10 minutes of the session
sig = np.where(m1.tod.values >= 22 * 60 + 50, -1, 0)
d, tr = H.run(sig, 0.5, 0.5, timeout=10, max_open=1, fill='FAIR', spread='base')
print('short-only signal at 22:50-22:59, TP/SL 0.5, timeout 10: trades %d, per trade %+.3f, per day %+.2f, win %.2f'
      % (len(tr), tr.pnl.mean(), d.pnl.mean(), (tr.pnl > 0).mean()))
sig = -sig
d, tr = H.run(sig, 0.5, 0.5, timeout=10, max_open=1, fill='FAIR', spread='base')
print('long-only  signal at 22:50-22:59, TP/SL 0.5, timeout 10: trades %d, per trade %+.3f, per day %+.2f, win %.2f'
      % (len(tr), tr.pnl.mean(), d.pnl.mean(), (tr.pnl > 0).mean()))
# first bar after break
fb = np.r_[True, H.day[1:] != H.day[:-1]]
x = m1[fb]
print('first bar of session: mean (open-low) %.2f, mean (high-open) %.2f, mean (close-open) %+.2f, recorded spread $%.2f'
      % ((x.open - x.low).mean(), (x.high - x.open).mean(), (x.close - x.open).mean(), x.spread_usd.mean()))
