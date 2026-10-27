"""Full evaluation battery for one pick on a given harness (used on TRAIN in s5_train_robust.py and once on TEST in
final_test.py). Rows: base (FAIR fills, bar spread + $0.05), recorded bar spread, flat $0.30, base + $0.07 commission,
OHLC fills, STOP fills, 1-bar latency, EA daily stop $15; baselines on the same entry bars: random directions (20 seeds),
always long, always short."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from sb import *


def daily_stop(T, limit=15.0):
    """Verbatim copy of ea/ea_replica.daily_stop (copied so nothing in ea/ is imported): drop the trades the EA would
    not open once the day's combined closed P&L is at or below -limit."""
    if limit <= 0: return T
    out = []
    for d, g in T.groupby(T.entry.dt.normalize()):
        cum = 0.0; hb = None
        for xi, p in sorted(zip(g.xi, g.pnl)):
            cum += p
            if cum <= -limit: hb = xi; break
        out.append(g if hb is None else g[g.ei < hb])
    return pd.concat(out)


def runp(H, f, p, sig=None, **over):
    s = fade_signal(f, *p['sig']) if sig is None else sig
    kw = dict(p['kw']); kw.update(over)
    if p['sim'] == 'x':
        return H.run_x(s, **kw)
    return H.run_lad(s, f.p3.values, **kw)


def with_daily_stop(H, d, t, limit=15.0):
    T = daily_stop(t.assign(xi=np.where(t.xi >= 0, t.xi, t.ei)), limit)
    dd = T.groupby(T.entry.dt.normalize()).pnl.sum().reindex(H.dates, fill_value=0.0)
    return pd.DataFrame({'pnl': dd.values, 'trades': 0}, index=H.dates), T


def battery(H, f, p, period, seeds=20):
    out = {}
    d, t = runp(H, f, p); out['base'] = summ(d, t, period)
    out['base']['breakeven_extra_cost'] = out['base']['per_trade']
    out['bar_spread'] = summ(*runp(H, f, p, spread='bar'), period)
    out['wide_0.30'] = summ(*runp(H, f, p, spread='wide'), period)
    out['commission_0.07'] = summ(d, t, period, fee=COMMISSION)
    out['OHLC'] = summ(*runp(H, f, p, fill='OHLC'), period)
    out['STOP'] = summ(*runp(H, f, p, fill='STOP'), period)
    out['latency1'] = summ(*runp(H, f, p, latency=1), period)
    out['daily_stop15'] = summ(*with_daily_stop(H, d, t), period)
    s = fade_signal(f, *p['sig'])
    rnd = [summ(*runp(H, f, p, sig=random_like(s, z)), period)['per_day'] for z in range(seeds)]
    out['random_same_bars'] = dict(per_day=float(np.mean(rnd)), sd=float(np.std(rnd)), best=float(np.max(rnd)),
                                   share_ge_pick=float(np.mean(np.array(rnd) >= out['base']['per_day'])))
    out['always_long'] = summ(*runp(H, f, p, sig=np.where(s != 0, 1.0, 0.0)), period)
    out['always_short'] = summ(*runp(H, f, p, sig=np.where(s != 0, -1.0, 0.0)), period)
    return out, d, t


def fmt(name, r):
    if 'win' not in r:
        return f'  {name:17s} {r["per_day"]:+7.2f}/day (sd {r["sd"]:.2f}, best seed {r["best"]:+.2f}, share of seeds >= pick {r["share_ge_pick"]:.2f})'
    return (f'  {name:17s} {r["per_day"]:+7.2f}/day {r["trades_day"]:6.1f} tr/day win {r["win"]:.2f} {r["per_trade"]:+.3f}/tr '
            f'days>=5 {r["days_ge5"]:.2f} losing {r["losing_days"]:.2f} worst day {r["worst_day"]:+7.1f} worst trade {r["worst_trade"]:+6.1f} '
            f'maxDD {r["max_dd"]:+7.1f} long {r["long_share"]:.2f}')
