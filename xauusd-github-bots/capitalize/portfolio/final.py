"""Score the train pick ONCE on 2022-01..2026-10, plus the common window alone and added to the pair.
PICK (max train $/day, >=10 trades/yr, from grid_train.csv): Donchian 120/60, both directions, D1 SMA200 regime, no GAA rule, no cut.
ALT (declared before the test: the exposure-capped version, best train among skip/skipclose): same + skipclose (0.02 lot cap)."""
from rules import *
import sys
pd.set_option('display.width', 220)
d = load('H1')
pg, pa = pair_daily(); pair = pg + pa; days = pair.index
g_tr, a_tr = pair_trades()


def intervals(t, lots_dir):
    return [(r.entry_time, r.exit_time, dr) for r, dr in zip(t.itertuples(), lots_dir)]


def exposure(third):
    """max simultaneous positions and max net long lots (0.01 units) over the common window, event sweep."""
    ev = []
    for r in g_tr.itertuples(): ev += [(r.entry_time, 1, 1), (r.exit_time, -1, -1)]
    for r in a_tr.itertuples(): ev += [(r.entry_time, 1, r.dir), (r.exit_time, -1, -r.dir)]
    for r in third.itertuples(): ev += [(r.entry_time, 1, int(r.dir)), (r.exit_time, -1, -int(r.dir))]
    ev.sort(key=lambda x: (x[0], x[1]))   # exits before entries at the same timestamp
    n = net = 0; mx = mxnet = 0; t3 = None; tm = pd.Timedelta(0); last = None
    for ts, k, dn in ev:
        if last is not None and n >= 3: tm += ts - last
        n += k; net += dn; mx = max(mx, n); mxnet = max(mxnet, net); last = ts
    return mx, mxnet, tm


def report(name, bot, dr, ga, rg, cut):
    d_, t, sig, kw = build(bot, dr, ga, rg)
    t = apply_cut(t, cut)
    print(f'\n===== {name}: {bot} {dr} gaa={ga} regime={rg} cut={cut} =====')
    res = {}
    for lab, (a, b) in [('train', TRAIN), ('test', TEST)]:
        tt, dd = window(t, d, a, b); tt = tt[tt.entry_time >= a]; p = daily(tt, dd)
        yrs = len(p) / 252
        nm, nmt, _ = losing_months(p)
        res[lab] = dict(per_day=round(p.mean(), 2), trades=len(tt), trades_yr=round(len(tt) / yrs, 1), win=round((tt.pnl > 0).mean() * 100, 1),
                        max_dd=round(maxdd(p)), losing_months=f'{nm}/{nmt}', long_share=round((tt.dir > 0).mean(), 2),
                        pnl_long=round(tt.pnl[tt.dir > 0].sum()), pnl_short=round(tt.pnl[tt.dir < 0].sum()), swap=round(tt.swap.sum()))
        print(lab, res[lab])
    print('by year', by_year(t, d))
    res['by_year'] = by_year(t, d)
    # coin flip, same entry bars, same exits, test window
    dte = d[d.index >= TEST[0] - pd.Timedelta(days=30)]
    cf = coinflip(d, sig, runs=100, seed=7, **kw)
    real = daily(t, d).mean()
    res['beats_random_full'] = round(float((cf < real).mean() * 100))
    print('coinflip full-period: real', round(real, 3), 'random median', round(float(np.median(cf)), 3), 'p95', round(float(np.percentile(cf, 95)), 3), 'beats', res['beats_random_full'], '%')
    # test-window coin flip (trades closed in test, entries in test)
    rng = np.random.default_rng(11); s = np.asarray(sig, float); nz = s != 0; cft = []
    for _ in range(100):
        r_ = s.copy(); r_[nz] = np.where(rng.random(nz.sum()) < .5, 1.0, -1.0)
        tr = simulate(d, r_, **kw); tt, dd = window(tr, d, *TEST); tt = tt[tt.entry_time >= TEST[0]]
        cft.append(daily(tt, dd).mean())
    cft = np.array(cft); res['beats_random_test'] = round(float((cft < res['test']['per_day']).mean() * 100))
    print('coinflip test: random median', round(float(np.median(cft)), 3), 'p95', round(float(np.percentile(cft, 95)), 3), 'beats', res['beats_random_test'], '%')
    # common window
    tc = t[t.entry_time >= COMMON]
    p3 = tc.groupby(tc.exit_time.dt.normalize()).pnl.sum().reindex(days, fill_value=0.0)
    comb = pair + p3
    nm3, nmt, _ = losing_months(p3); nmc, _, mc = losing_months(comb); nmp, _, mp = losing_months(pair)
    res['common'] = dict(alone=round(p3.mean(), 2), alone_dd=round(maxdd(p3)), alone_losing_months=f'{nm3}/{nmt}', trades=len(tc),
                         win=round((tc.pnl > 0).mean() * 100, 1),
                         with_pair=round(comb.mean(), 2), with_pair_dd=round(maxdd(comb)), with_pair_losing=f'{nmc}/{nmt}',
                         pair=round(pair.mean(), 2), pair_dd=round(maxdd(pair)), pair_losing=f'{nmp}/{nmt}',
                         corr_daily=round(np.corrcoef(p3, pair)[0, 1], 2), corr_monthly=round(np.corrcoef(p3.groupby(p3.index.to_period('M')).sum(), mp)[0, 1], 2),
                         worst_month_with_pair=round(mc.min()), worst_day_with_pair=round(comb.min()))
    print('common', res['common'])
    mx, mxnet, tm3 = exposure(tc)
    res['max_open'] = mx; res['max_net_long'] = mxnet; res['time_3open_h'] = round(tm3.total_seconds() / 3600)
    print('max simultaneous positions (0.01 each):', mx, '| max net long lots x0.01:', mxnet, '| hours with 3 open:', res['time_3open_h'])
    print('monthly with pair:', (mc).round(0).astype(int).to_dict())
    print('monthly third alone:', p3.groupby(p3.index.to_period('M')).sum().round(0).astype(int).to_dict())
    # trade-list sanity
    assert (t.exit_time >= t.entry_time).all()
    ov = (t.entry_time.values[1:] < t.exit_time.values[:-1]).sum()
    print('sanity: overlapping own trades', ov, '| exit reasons', t.why.value_counts().to_dict(), '| worst trade', round(t.pnl.min(), 1), 'best', round(t.pnl.max(), 1))
    return res, t


R = {}
R['pick'], tpick = report('PICK', 'donchian', 'both', 'none', 'sma200', 'none')
R['alt'], talt = report('ALT (0.02 cap)', 'donchian', 'both', 'skipclose', 'sma200', 'none')
for k in ['pick', 'alt']:
    pass
tpick.drop(columns=['ei', 'xi']).round(2).to_csv(OUT + 'trades_pick.csv', index=False)
hg, _ = hold_gold(d, *TEST); hc, _ = hold_gold(d, COMMON, TEST[1])
print('\nhold 0.01 lot incl swap: test', round(hg, 2), 'common', round(hc, 2))
import json; json.dump(R, open(OUT + 'final_summary.json', 'w'), default=str, indent=1)
