"""FINAL: the three picks, locked on TRAIN (screen1-5), scored ONCE on TEST (2026-09-01..2026-10-09).
Engine: ea_sim._sim_next (entry at the next bar's open) with ea_replica.run_ea's entry filters.
Reported per pick and period: FAIR/base default; OHLC and STOP fills; recorded bar spread, flat $0.30, base + $0.07
commission; 1-bar latency; random directions on the same bars (20 seeds); always-long / always-short on the same
bars; breakeven extra cost per trade (bisection). Writes final_test.json and final_<pick>_trades.csv."""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch')
from feats import *
from simlib import EASim, stats, random_like

OUT = '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch/'
E = EASim(); m = E.H.m1; f = features(m)
ok_bar = valid(m, f) & E.ok & (m.tod.values >= 65) & (m.tod.values <= 22 * 60 + 29) & ~m.last_of_session.values
onset = lambda s0: np.where(np.r_[0, s0[:-1]] == s0, 0, s0)
run44 = onset(sig_run(f, 4, 4))
rz = both(sig_rsi(f, 3, 97.5), sig_z(f, 60, 2))
PICKS = {
    'P1_RUN44': (run44, dict(tp=1000, sl=12, timeout=3, max_open=1, cooldown=0)),
    'P2_RSI3Z60': (rz, dict(tp=1000, sl=12, timeout=5, max_open=3, cooldown=0)),
    'P3_RUN44_or_RSI3Z60on': (union(run44, onset(rz)), dict(tp=1000, sl=12, timeout=3, max_open=3, cooldown=0)),
}


def pdays(s, period, **kw):
    d, t = E.run(s, **kw); return stats(d, t, period)['per_day']


def breakeven(s, period, kw):
    lo, hi = -1.0, 3.0
    if pdays(s, period, extra=lo, **kw) < 0: return lo
    if pdays(s, period, extra=hi, **kw) > 0: return hi
    for _ in range(30):
        mid = (lo + hi) / 2
        if pdays(s, period, extra=mid, **kw) > 0: lo = mid
        else: hi = mid
    return (lo + hi) / 2


res = {}
for name, (s, kw) in PICKS.items():
    s = np.where(ok_bar, s, 0)
    d, t = E.run(s, **kw)
    t.to_csv(OUT + f'final_{name}_trades.csv', index=False)
    r = {}
    for per in ('train', 'h1', 'h2', 'test'):
        st = stats(d, t, per)
        x = {k: (float(v) if v is not None else None) for k, v in st.items()}
        if per in ('train', 'test'):
            x['ohlc'] = pdays(s, per, fill='OHLC', **kw); x['stop'] = pdays(s, per, fill='STOP', **kw)
            x['bar'] = pdays(s, per, spread='bar', **kw); x['wide'] = pdays(s, per, spread='wide', **kw)
            x['commission'] = pdays(s, per, extra=0.07, **kw); x['latency1'] = pdays(s, per, latency=1, **kw)
            rr = [pdays(random_like(s, z), per, **kw) for z in range(20)]
            x['random_mean'] = float(np.mean(rr)); x['random_sd'] = float(np.std(rr))
            x['random_beats_pick'] = float(np.mean(np.array(rr) >= st['per_day']))
            x['always_long'] = pdays(np.abs(s), per, **kw); x['always_short'] = pdays(-np.abs(s), per, **kw)
            x['breakeven_extra'] = breakeven(s, per, kw)
            if per == 'test':
                tt = t[t.entry >= SPLIT]; dd = d[d.index >= SPLIT]
                x['test_halves'] = [float(dd.pnl[dd.index < pd.Timestamp('2026-09-20')].mean()),
                                    float(dd.pnl[dd.index >= pd.Timestamp('2026-09-20')].mean())]
                x['avg_win'] = float(tt.pnl[tt.pnl > 0].mean()); x['avg_loss'] = float(tt.pnl[tt.pnl <= 0].mean())
                x['stops_hit'] = int((tt.pnl <= -kw['sl'] + 0.5).sum())
                x['long_pnl_per_trade'] = float(tt.pnl[tt.dir == 1].mean()); x['short_pnl_per_trade'] = float(tt.pnl[tt.dir == -1].mean())
        r[per] = x
    res[name] = dict(rule=kw, **r)
    print(f'=== {name} {kw}')
    for per in ('train', 'test'):
        x = r[per]
        print(f"  {per.upper():5s} {x['per_day']:+.2f}/day  {x['trades_day']:.1f} trades/day  win {x['win']:.2f}  {x['per_trade']:+.3f}/trade  "
              f"days>=5 {x['days_ge5']:.2f}  losing days {x['losing_days']:.2f}  worst day {x['worst_day']:+.1f}  worst trade {x['worst_trade']:+.2f}  "
              f"maxDD {x['max_dd']:+.1f}  long share {x['long_share']:.2f}")
        print(f"        OHLC {x['ohlc']:+.2f} STOP {x['stop']:+.2f} | bar spread {x['bar']:+.2f} flat0.30 {x['wide']:+.2f} +comm {x['commission']:+.2f} | "
              f"latency1 {x['latency1']:+.2f} | random {x['random_mean']:+.2f} (sd {x['random_sd']:.2f}, share >= pick {x['random_beats_pick']:.2f}) | "
              f"always-long {x['always_long']:+.2f} always-short {x['always_short']:+.2f} | breakeven extra cost {x['breakeven_extra']:+.3f}/trade")
    print(f"  TRAIN halves {r['h1']['per_day']:+.2f} / {r['h2']['per_day']:+.2f};  TEST halves (Sep 1-19 / Sep 20-Oct 9) "
          f"{r['test']['test_halves'][0]:+.2f} / {r['test']['test_halves'][1]:+.2f};  TEST avg win {r['test']['avg_win']:+.2f} avg loss {r['test']['avg_loss']:+.2f} "
          f"stops {r['test']['stops_hit']}; long/short $/trade {r['test']['long_pnl_per_trade']:+.3f}/{r['test']['short_pnl_per_trade']:+.3f}")
json.dump(res, open(OUT + 'final_test.json', 'w'), indent=1, default=float)
