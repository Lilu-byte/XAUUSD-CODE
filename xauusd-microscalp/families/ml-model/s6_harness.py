"""Stage 6 (TRAIN only): harness runs (mlib v2, FAIR/base) of the shortlisted picks on their walk-forward OOS signals
(Jul20-Aug31) over max_open x cooldown, with the random-direction baseline on the same bars (20 seeds).
usage: python3 s6_harness.py 'key~q~cen~tp~sl~to' ..."""
import sys, glob
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *

H = Harness(); m1 = H.m1; T = m1.index
scores = {}
for f in sorted(glob.glob(FAM + 'tmp_s1*.npz')):
    z = np.load(f); idx = z['idx']
    for k in z.files:
        if k != 'idx': scores[k] = z[k]


def summ(days, trades, lo=B[0], hi=B[3]):
    d = days[(days.index >= lo) & (days.index < hi)]; t = trades[(trades.entry >= lo) & (trades.entry < hi)]
    p = d.pnl; eq = p.cumsum()
    return dict(per_day=p.mean(), trades_day=len(t) / len(d), win=(t.pnl > 0).mean(), per_trade=t.pnl.mean(),
                days_ge5=(p >= 4.99).mean(), worst_day=p.min(), max_dd=(eq - eq.cummax()).min(),
                f1=d.pnl[d.index < B[1]].mean(), f2=d.pnl[(d.index >= B[1]) & (d.index < B[2])].mean(), f3=d.pnl[d.index >= B[2]].mean())


pd.set_option('display.width', 220)
n_runs = 0
for arg in sys.argv[1:]:
    key, q, cen, tp, sl, to = arg.split('~'); tp, sl, to = float(tp), float(sl), int(to)
    sg = signal_q(scores[key], float(q), center=bool(int(cen)))
    sig = np.zeros(len(m1), np.int64); sig[idx] = sg
    rows = []
    for mo in (1, 2, 3, 5, 50):
        for cd in (0, 2, 5):
            d, t = H.run(sig, tp, sl, timeout=to, max_open=mo, cooldown=cd); n_runs += 1
            r = dict(max_open=mo, cooldown=cd, **summ(d, t))
            rnd = [summ(*H.run(random_like(sig, s), tp, sl, timeout=to, max_open=mo, cooldown=cd))['per_day'] for s in range(20)]
            n_runs += 20
            r['rand_per_day'] = np.mean(rnd); r['rand_sd'] = np.std(rnd)
            rows.append(r)
    print(f'\n{arg}  (OOS Jul20-Aug31, 31 days)')
    print(pd.DataFrame(rows).round(3).to_string(index=False))
print('harness runs', n_runs)
