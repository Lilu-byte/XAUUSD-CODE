"""(2) random-direction baseline (50 seeds) + always long/short on the same bars; (3) costs, fills, latency, spread gate,
exit at the next open, stop slippage. Every variant keeps the rule's parameters fixed (no re-optimisation)."""
import json
from common import *

R = Rep(); m = R.m; H = R.H
raw = raw_signal(m.close.values)
s0 = entry_filter(m, raw)
res = {}


def both(name, days, T, fee=0.0):
    r = {p: stats(days, T, p, fee) for p in ('train', 'test')}
    res[name] = r
    print(fmt(name + ' TRAIN', r['train'])); print(fmt(name + ' TEST', r['test']))
    return r


base = both('base', *R.run(s0))
# (2) baselines on the same filtered entry bars
rnd = {'train': [], 'test': []}
for z in range(50):
    d, T = R.run(random_like(s0, 1000 + z))
    for p in rnd: rnd[p].append(stats(d, T, p)['per_day'])
for p in rnd:
    x = np.array(rnd[p])
    res[f'random50_{p}'] = dict(mean=x.mean(), sd=x.std(), best=x.max(), worst=x.min(),
                                share_beating_pick=float((x >= base[p]['per_day']).mean()))
    print(f'random directions 50 seeds {p.upper()}: mean {x.mean():+.2f} sd {x.std():.2f} best {x.max():+.2f} '
          f'share of seeds >= pick {(x >= base[p]["per_day"]).mean():.2f}')
both('always_long', *R.run(np.where(s0 != 0, 1, 0)))
both('always_short', *R.run(np.where(s0 != 0, -1, 0)))

# (3) costs
both('bar_spread', *R.run(s0, spread='bar'))
d, T = R.run(s0); both('base+commission0.07', d, T, fee=0.07)
both('flat0.30', *R.run(s0, spread=0.30))
both('flat0.40', *R.run(s0, spread=0.40))
both('base+0.10', *R.run(s0, spread='base+0.10'))
for f in ('OHLC', 'STOP'):
    both('fill_' + f, *R.run(s0, fill=f))
for L in (1, 2):
    both(f'latency{L}', *R.run(entry_filter(m, raw, lat=L)))
both('entry_spread<=0.30', *R.run(entry_filter(m, raw, max_spread=0.30)))
both('entry_spread<=0.30+commission', *R.run(entry_filter(m, raw, max_spread=0.30)), fee=0.07)

# execution details the bar simulator glosses over (independent python simulator)
t_ns = m.index.values.astype(np.int64)
def py(name, fee=0.0, **kw):
    out = sim_py(H.o, H.h, H.l, H.c, t_ns, R.spr(kw.pop('spread', 'base')), H.tod, H.day, H.last, s0, **kw)
    P = pd.DataFrame(out, columns=['ei', 'xi', 'dir', 'pnl']); P['entry'] = m.index[P.ei.values]
    dP = P.groupby(P.entry.dt.normalize()).pnl.sum().reindex(R.dates, fill_value=0.0)
    return both(name, dP, P, fee=fee)
py('exit_at_next_open(EA)', exit_next_open=True)
py('stop_slippage_0.50', stop_slip=0.5)
py('stop_slippage_1.00', stop_slip=1.0)
py('next_open+slip0.5+commission', fee=0.07, exit_next_open=True, stop_slip=0.5)
py('next_open+slip0.5+comm+flat0.30', fee=0.07, exit_next_open=True, stop_slip=0.5, spread=0.30)

# breakeven extra cost per trade
for p in ('train', 'test'):
    print(f'breakeven extra cost per trade {p.upper()}: {base[p]["per_trade"]:+.3f} (base spread already paid)')

# spread conditions on the trades' bars vs. all bars (recorded = bar MINIMUM spread)
sp = m.spread.values  # points, raw (zeros = not recorded)
ent = T.ei.values + 1
ok = sp > 0
print('recorded spread (points, non-zero bars): all bars median %.0f mean %.1f | entry bars median %.0f mean %.1f | '
      'signal bars median %.0f mean %.1f' % (np.median(sp[ok]), sp[ok].mean(), np.median(sp[ent][sp[ent] > 0]), sp[ent][sp[ent] > 0].mean(),
                                            np.median(sp[T.ei.values][sp[T.ei.values] > 0]), sp[T.ei.values][sp[T.ei.values] > 0].mean()))
rng_all = (m.high - m.low).values
print('bar range $: all bars median %.2f | entry bars median %.2f | tick volume all median %.0f | entry bars median %.0f'
      % (np.median(rng_all), np.median(rng_all[ent]), m.tick_volume.median(), np.median(m.tick_volume.values[ent])))
json.dump(res, open(OUT + 'v2_battery.json', 'w'), indent=1, default=float)
