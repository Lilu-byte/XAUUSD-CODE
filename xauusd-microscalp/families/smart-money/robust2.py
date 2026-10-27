"""TRAIN neighbourhood check of the two surviving clusters:
(1) fade of the N-bar M1 breakout in a session window, (2) sweep->confirmation entry model in the late session.
Fixed brackets; reports TRAIN per_day, per_trade, Jul/Aug halves."""
import sys, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from sigs2 import *
from mlib import Harness, summarize
H = Harness(); m1 = H.m1; o, h, l, c = arrs(m1); tod = m1.tod.values
JUL = pd.Timestamp('2026-08-01')
pd.set_option('display.width', 250)


def tr_stats(sig, tp, sl, to, mo=1, **kw):
    days, t = H.run(sig, tp, sl, timeout=to, max_open=mo, **kw)
    d = days[days.index < SPLIT].pnl; t = t[t.entry < SPLIT]
    return dict(per_day=d.mean(), n_day=len(t) / len(d), pt=t.pnl.mean(), win=(t.pnl > 0).mean(),
                jul=d[d.index < JUL].mean(), aug=d[d.index >= JUL].mean(), worst=d.min())


rows = []
WIN = {'lon10-15': (600, 900), 'lon10-13': (600, 780), 'lon11-15': (660, 900), 'lon9-15': (540, 900),
       'lon10-16': (600, 960), 'ny15-19': (900, 1140), 'asia1-10': (60, 600), 'all': (0, 1440)}
for N, (wn, (a, b)) in itertools.product((15, 20, 30, 45, 60), WIN.items()):
    sig = np.where((tod >= a) & (tod < b), -breakout(o, h, l, c, N), 0)
    for br in ((1.0, 10.0, 30), (0.75, 10.0, 20), (0.5, 3.0, 10)):
        r = tr_stats(sig, *br); r.update(cl='fade_brk', N=N, win=wn, br=br); rows.append(r)
df = pd.DataFrame(rows)
print('fade N-bar breakout, TRAIN per_day by N x window (bracket tp1/sl10/to30, mo1):')
print(df[df.br == (1.0, 10.0, 30)].pivot(index='N', columns='win', values='per_day').round(2).to_string())
print('\n... bracket tp0.75/sl10/to20:')
print(df[df.br == (0.75, 10.0, 20)].pivot(index='N', columns='win', values='per_day').round(2).to_string())
print('\n... bracket tp0.5/sl3/to10:')
print(df[df.br == (0.5, 3.0, 10)].pivot(index='N', columns='win', values='per_day').round(2).to_string())

rows = []
for N, W, cf, (wn, (a, b)) in itertools.product((15, 30, 60), (5, 15), (0, 1, 2),
                                                 {'late19-23': (1140, 1440), 'all': (0, 1440), 'ny15-19': (900, 1140), 'lon10-15': (600, 900)}.items()):
    sig = np.where((tod >= a) & (tod < b), sweep_then(o, h, l, c, N, W, cf, 0.2), 0)
    for br in ((0.5, 2.0, 5), (1.0, 3.0, 10)):
        r = tr_stats(sig, *br, mo=3); r.update(N=N, W=W, cf=cf, win=wn, br=br); rows.append(r)
d2 = pd.DataFrame(rows)
print('\nsweep->confirmation entry model, TRAIN per_day (bracket tp1/sl3/to10, mo3):')
print(d2[d2.br == (1.0, 3.0, 10)].pivot_table(index=['N', 'W', 'cf'], columns='win', values='per_day').round(2).to_string())
print('\n... n/day:')
print(d2[d2.br == (1.0, 3.0, 10)].pivot_table(index=['N', 'W', 'cf'], columns='win', values='n_day').round(1).to_string())
print('\nconfigs in this script:', len(df) + len(d2))
