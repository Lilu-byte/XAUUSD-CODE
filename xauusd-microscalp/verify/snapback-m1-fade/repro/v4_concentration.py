"""(5) Is the profit spread over many days and both directions? Top-N day shares, per-week, day-bootstrap, t-stat,
P&L by direction, by hour, and with the largest trades removed."""
from common import *

R = Rep(); m = R.m
s0 = entry_filter(m, raw_signal(m.close.values))
days, T = R.run(s0)
rng = np.random.default_rng(7)
for per, sel in (('TRAIN', days.index < SPLIT), ('TEST', days.index >= SPLIT)):
    d = days[sel]; srt = d.sort_values(ascending=False)
    t = T[(T.entry >= SPLIT) == (per == 'TEST')]
    bs = np.array([rng.choice(d.values, len(d)).mean() for _ in range(10000)])
    tstat = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    print(f'{per}: {len(d)} days total {d.sum():+.1f}  mean {d.mean():+.2f}/day sd {d.std():.1f}  t={tstat:.2f}  '
          f'day-bootstrap 95% CI [{np.percentile(bs, 2.5):+.2f}, {np.percentile(bs, 97.5):+.2f}]  P(mean<=0) {np.mean(bs <= 0):.3f}')
    print(f'   best 5 days {srt.iloc[:5].round(1).tolist()} = {srt.iloc[:5].sum():+.1f} '
          f'({srt.iloc[:5].sum() / d.sum():.0%} of total); best 3 = {srt.iloc[:3].sum() / d.sum():.0%}; '
          f'mean/day without best 3 {srt.iloc[3:].mean():+.2f}, without best 5 {srt.iloc[5:].mean():+.2f}; '
          f'median day {d.median():+.2f}; winning days {(d > 0).mean():.2f}')
    print(f'   worst 5 days {srt.iloc[-5:].round(1).tolist()}')
    wk = d.groupby(d.index.to_period('W')).sum()
    print('   weekly $: ' + ' '.join(f'{v:+.0f}' for v in wk.values))
    for dr, nm in ((1, 'long (fade down-moves)'), (-1, 'short (fade up-moves)')):
        x = t[t.dir == dr]
        dd = x.groupby(x.entry.dt.normalize()).pnl.sum().reindex(d.index, fill_value=0)
        print(f'   {nm}: {len(x)} trades {x.pnl.sum():+.1f} ({x.pnl.mean():+.3f}/tr), {dd.mean():+.2f}/day, '
              f'without its best 3 days {dd.sort_values(ascending=False).iloc[3:].sum():+.1f}')
    hr = t.groupby(t.entry.dt.hour).pnl.agg(['size', 'sum'])
    top = hr.sort_values('sum', ascending=False)
    print('   by hour (server) top 3: ' + ', '.join(f'{h}h n={int(r["size"])} {r["sum"]:+.0f}' for h, r in top.head(3).iterrows())
          + ' | bottom 3: ' + ', '.join(f'{h}h n={int(r["size"])} {r["sum"]:+.0f}' for h, r in top.tail(3).iterrows()))
    tp = t.pnl.sort_values(ascending=False).values
    for k in (5, 10, 20):
        print(f'   without the best {k} trades: {tp[k:].sum():+.1f} total, {tp[k:].sum() / len(d):+.2f}/day')
# the three best TEST days: what happened
d = days[days.index >= SPLIT].sort_values(ascending=False)
for dt in d.index[:3]:
    t = T[T.entry.dt.normalize() == dt]
    mm = m[m.index.normalize() == dt]
    print(f'{dt.date()}: {d[dt]:+.1f} from {len(t)} trades (long {int((t.dir == 1).sum())}), day range ${mm.high.max() - mm.low.min():.0f}, '
          f'best trade {t.pnl.max():+.1f}, signals per hour max {t.groupby(t.entry.dt.hour).size().max()}')
