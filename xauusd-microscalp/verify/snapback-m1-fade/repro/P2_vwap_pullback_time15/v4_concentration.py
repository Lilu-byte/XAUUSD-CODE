"""(5) Is the profit spread over many days / both directions / many independent events? Fixed rule, no selection."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/repro/P2_vwap_pullback_time15')
from p2lib import *
R = Rep(); m = R.m
raw, *_ = signal_df(m)
s = entry_filter(m, raw)
d, T = R.run(s)
rng = np.random.default_rng(0)
for per, sel in (('TRAIN', d.index < SPLIT), ('TEST', d.index >= SPLIT)):
    x = d[sel]; t = T[(T.entry >= SPLIT) == (per == 'TEST')].copy()
    xs = x.sort_values(ascending=False)
    pos = x[x > 0].sum()
    bs = np.array([rng.choice(x.values, len(x)).mean() for _ in range(10000)])
    print(f'{per}: {len(x)} days, total {x.sum():+.1f}; top-5 days {xs.iloc[:5].round(1).tolist()} = {xs.iloc[:5].sum():+.1f} '
          f'= {xs.iloc[:5].sum() / x.sum():.2f} of total ({xs.iloc[:5].sum() / pos:.2f} of gross positive days); '
          f'per day ex top-1 {xs.iloc[1:].mean():+.2f}, ex top-3 {xs.iloc[3:].mean():+.2f}, ex top-5 {xs.iloc[5:].mean():+.2f}; '
          f'median day {x.median():+.2f}; positive days {(x > 0).mean():.2f}; day-bootstrap 90% CI [{np.percentile(bs, 5):+.2f}, '
          f'{np.percentile(bs, 95):+.2f}], P(mean<=0) {(bs <= 0).mean():.2f}')
    for dn, nm in ((1, 'long'), (-1, 'short')):
        tt = t[t.dir == dn]
        dd = tt.groupby(tt.entry.dt.normalize()).pnl.sum().reindex(x.index, fill_value=0)
        print(f'   {nm:5s}: {len(tt)} trades, ${tt.pnl.sum():+.1f}, {tt.pnl.mean():+.3f}/tr, win {(tt.pnl > 0).mean():.2f}, '
              f'{dd.mean():+.2f}/day, top-5 days {dd.sort_values(ascending=False).iloc[:5].sum():+.1f}')
    # independent events: signals closer than the 15-bar hold belong to one event (stacked up to 3 positions)
    ei = np.sort(t.ei.values); ev = np.r_[1, (np.diff(ei) > HOLD).astype(int)].cumsum()
    t = t.sort_values('ei'); t['ev'] = ev
    g = t.groupby('ev').pnl.sum()
    gs = g.sort_values(ascending=False)
    print(f'   independent events (entries > {HOLD} bars apart): {len(g)} ({len(g) / len(x):.1f}/day), positions/event '
          f'{len(t) / len(g):.2f}; event P&L mean {g.mean():+.2f} sd {g.std():.2f} t {g.mean() / (g.std() / np.sqrt(len(g))):+.2f}; '
          f'top-5 events {gs.iloc[:5].round(1).tolist()} = {gs.iloc[:5].sum() / g.sum() if g.sum() > 0 else float("nan"):.2f} of total')
    w = x.groupby(x.index.to_period('W')).sum()
    print('   weekly $: ' + ' '.join(f'{v:+.0f}' for v in w.values))
    # trend context: underlying move of gold over the period
    mm = m[(m.index >= SPLIT) == (per == 'TEST')]
    print(f'   gold close {mm.close.iloc[0]:.1f} -> {mm.close.iloc[-1]:.1f} ({mm.close.iloc[-1] - mm.close.iloc[0]:+.1f})')
# direction-mix decomposition on TEST: expected per trade of a random-direction rule with the pick's long share
for per in ('train', 'test'):
    dl, Tl = R.run(entry_filter(m, np.where(raw != 0, 1.0, 0.0))); ds_, Ts = R.run(entry_filter(m, np.where(raw != 0, -1.0, 0.0)))
    pl = stats(dl, Tl, per)['per_trade']; ps = stats(ds_, Ts, per)['per_trade']; r = stats(d, T, per)
    mix = r['long_share'] * pl + (1 - r['long_share']) * ps
    print(f'{per.upper()} same bars: always-long {pl:+.3f}/tr, always-short {ps:+.3f}/tr; random direction with the pick\'s '
          f'long share {r["long_share"]:.2f} -> {mix:+.3f}/tr; pick {r["per_trade"]:+.3f}/tr; direction-skill residual '
          f'{r["per_trade"] - mix:+.3f}/tr')
