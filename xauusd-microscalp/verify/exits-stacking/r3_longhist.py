"""Step 4b: the same grid basket rule (step $2, max 50, basket +$0.30, no stop, session-end close) on LONGER history,
using the M5 file (2025-05..2026-10) and the M15 file (2022-07..2026-10). The M1 MR signal cannot be computed there, so an
analogue on the coarser bars is used: fade |close[i]-close[i-1]| > k x mean(high-low, last 4 hours of bars).
The proxy is validated on the months where M1 also exists (2026-06-26..2026-10-09): if it reproduces the M1 result there
(near-100% basket wins, no failures, positive per day), its behaviour on the earlier months is informative.
Session handling mirrors mlib v2: entries only on bars that close between 01:05 and 22:30, force-close at the close of the
bar that ends at/just before 23:00 server, never carried over a session break."""
from common import *

pd.set_option('display.width', 250)


def prep(tf):
    d = mlib.load(tf).copy()
    sp = d.spread.copy()
    med = sp[sp > 0].groupby(sp[sp > 0].index.hour).median()
    z = sp <= 0
    sp[z] = d.index[z].hour.map(med).values
    d['spread_usd'] = sp * 0.01
    d['tod'] = d.index.hour * 60 + d.index.minute
    nxt = d.index.to_series().shift(-1)
    d['last_of_session'] = ((nxt - d.index.to_series()) > pd.Timedelta(minutes=30 + mlib.MIN[tf])) | nxt.isna()
    return d


M1_START = pd.Timestamp('2026-06-26'); SPLIT = mlib.SPLIT
CFG = {'M5': dict(first_tod=65, last_tod=22 * 60 + 25, end_tod=22 * 60 + 55, win=48),
       'M15': dict(first_tod=60, last_tod=22 * 60 + 15, end_tod=22 * 60 + 45, win=16)}
PER = [('pre-M1', None, M1_START), ('M1-TRAIN months', M1_START, SPLIT), ('M1-TEST months', SPLIT, None)]

allrows = []
for tf in ('M5', 'M15'):
    d = prep(tf); gg = G(d); cf = CFG[tf]
    kw = dict(first_tod=cf['first_tod'], last_tod=cf['last_tod'], end_tod=cf['end_tod'])
    print(f'\n######## {tf}: {d.index[0]} .. {d.index[-1]}  bars {len(d)}')
    for k in (1.5, 2.0, 2.5, 3.0):
        sig = mr_signal(d, look=1, k=k, win=cf['win'])
        for dirmode in ('fade', 'random'):
            s = sig if dirmode == 'fade' else mlib.random_like(sig, 99)
            runs = [gg.run(s, seed=sd, **kw) for sd in range(3)]
            for name, lo, hi in PER:
                df = pd.DataFrame([summ(gg, *r, lo=lo, hi=hi) for r in runs])
                row = dict(tf=tf, k=k, dir=dirmode, period=name, per_day=df.per_day.mean(), baskets_day=df.baskets_day.mean(),
                           basket_win=df.basket_win.mean(), n_forced=df.n_forced.mean(), forced_pnl=df.forced_pnl.mean(),
                           worst_day=df.worst_day.min(), losing_days=df.losing_days.mean(), max_dd_float=df.max_dd_float.min(),
                           max_dd_closed=df.max_dd_closed.min(), total=df.total.mean(), days=df.days.mean(),
                           sig_day=None)
                allrows.append(row)
                print(f'{tf} k {k} {dirmode:6s} {name:16s} per_day {row["per_day"]:+8.2f} bsk/day {row["baskets_day"]:5.1f} bwin {row["basket_win"]:.4f} '
                      f'forced {row["n_forced"]:5.1f} (pnl {row["forced_pnl"]:+9.0f}) worst_day {row["worst_day"]:+8.0f} losing_days {row["losing_days"]:.3f} '
                      f'maxDD closed {row["max_dd_closed"]:+8.0f} float {row["max_dd_float"]:+8.0f} total {row["total"]:+9.0f} days {row["days"]:.0f}')
R = pd.DataFrame(allrows)
R.to_csv(VOUT + 'r3_longhist.csv', index=False)
