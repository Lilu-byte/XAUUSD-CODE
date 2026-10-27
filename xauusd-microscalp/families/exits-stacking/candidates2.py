"""TRAIN-only evaluation of the shortlisted configurations before freezing the final picks:
summary, inner halves, random direction on the same bars (20 seeds), stacking / day-limit variants, and for the
grid: in-bar path sensitivity (FAIR seeds, OHLC), stress loss of a one-way move, and the TRAIN trend days."""
from sigs2 import *
from gridsim2 import *

m1, H = train_harness(); S = build(m1); tr = m1.index < SPLIT
mrg = gate(S['MR'], m1, 0.10)[tr]
pd.set_option('display.width', 250)


def line(name, r):
    print(f'  {name:42s} per_day {r["per_day"]:+6.2f} trades/day {r["trades_day"]:5.1f} pwin {r["pwin"]:.2f} per_trade {r["per_trade"]:+.3f} '
          f'worst {r["worst_day"]:+7.1f} maxDD {r["max_dd"]:+7.1f} days>=5 {r["days_ge5"]:.2f} jul {r["pd_jul"]:+.2f} aug {r["pd_aug"]:+.2f}')


print('A) MR (fade 3-bar move > 3 x ATR240) gated at recorded spread <= 0.10, TP 0.75 SL 20 timeout 10')
d, t = run_pw(H, mrg, 0.75, 20.0, timeout=10); line('max_open 1 (pick A)', summ(d, t, 'train'))
rnd = [summ(*run_pw(H, random_like(mrg, s), 0.75, 20.0, timeout=10), 'train')['per_day'] for s in range(20)]
print(f'  random direction same bars (20 seeds): {np.mean(rnd):+.2f}/day (sd {np.std(rnd):.2f})')
print('  edge (TRAIN rows):'); print(edge(m1[tr], mrg, horizons=(1, 3, 5, 10)).loc[['train']].round(3).to_string())
for mo, cd in ((3, 0), (5, 0), (10, 0), (5, 2), (50, 0)):
    line(f'max_open {mo} cooldown {cd}', summ(*run_pw(H, mrg, 0.75, 20.0, timeout=10, max_open=mo, cooldown=cd), 'train'))
for dt, dl in ((5, 0), (0, 10), (0, 20), (5, 20)):
    acc = pd.DataFrame([summ(*run_pw(H, mrg, 0.75, 20.0, timeout=10, day_target=dt, day_loss=dl, fill='RAND', seed=s), 'train') for s in range(5)]).mean()
    line(f'day_target {dt} day_loss {dl} (RAND x5)', acc)
for fill, sp in (('OHLC', 'base'), ('FAIR', 'bar'), ('FAIR', 'wide')):
    line(f'{fill}/{sp}', summ(*run_pw(H, mrg, 0.75, 20.0, timeout=10, fill=fill, spread=sp), 'train'))

print('\nB) MR grid: basket direction = MR signal (ungated), add every $2 against, up to 50, close all at +$0.30, no stop')
sig = S['MR'][tr]
for path, seed in (('FAIR', 0), ('FAIR', 1), ('FAIR', 2), ('OHLC', 0)):
    days, bask, eqm, levm = run_grid(H, sig, 2.0, 50, 0.3, 0.0, tmax=0, path=path, seed=seed)
    g = gsumm(H, days, bask, eqm, levm, 'train')
    print(f'  {path} seed {seed}: per_day {g["per_day"]:+.2f} baskets/day {g["baskets_day"]:.1f} positions/day {g["positions_day"]:.1f} '
          f'per_position {g["per_position"]:+.3f} worst_day {g["worst_day"]:+.1f} worst_intraday {g["worst_intraday"]:+.1f} '
          f'max_levels {g["max_levels"]} min margin level 1:100 {g["min_margin_level_1to100"]:.2f} days>=5 {g["days_ge5"]:.2f}')
rg = []
for s in range(20):
    days, bask, eqm, levm = run_grid(H, random_like(sig, s), 2.0, 50, 0.3, 0.0, tmax=0, seed=s)
    rg.append(gsumm(H, days, bask, eqm, levm, 'train'))
rg = pd.DataFrame(rg)
print(f'  random direction baskets on the same MR bars (20 seeds): per_day {rg.per_day.mean():+.2f} (sd {rg.per_day.std():.2f}), '
      f'worst_day median {rg.worst_day.median():+.1f} min {rg.worst_day.min():+.1f}, seeds with a stop-out at 1:100: {rg.stopout_1to100.sum()}')
days, bask, eqm, levm = run_grid(H, sig, 2.0, 50, 0.3, 0.0, tmax=0)
print('  basket depth distribution (levels used):', bask.levels.value_counts().sort_index().to_dict())
for step, btp in ((1.0, 0.3), (2.0, 0.1), (2.0, 0.5), (3.0, 0.3)):
    dd, bb, ee, ll = run_grid(H, sig, step, 50, btp, 0.0, tmax=0)
    g = gsumm(H, dd, bb, ee, ll, 'train')
    print(f'  neighbour step {step} btp {btp}: per_day {g["per_day"]:+.2f} worst_day {g["worst_day"]:+.1f} jul {dd.pnl[dd.index < HALF].mean():+.2f} aug {dd.pnl[dd.index >= HALF].mean():+.2f}')
print('  stress: loss of one basket if price runs $D against it and never retraces before the forced close (step 2, 50 levels):')
for D in (20, 40, 66, 87, 100, 150, 200):
    n = min(50, int(D // 2) + 1)
    loss = n * D - 2.0 * n * (n - 1) / 2 + 0.21 * n
    margin100 = n * 4400 / 100
    print(f'    D=${D:3d}: {n:2d} positions, loss ${loss:7.0f}, equity left ${3000 - loss:7.0f}, margin at 1:100 ${margin100:5.0f} '
          f'-> {"STOP-OUT / blown" if 3000 - loss < 0.5 * margin100 else "survives"}')
D1 = m1[tr].groupby(m1[tr].index.normalize()).agg(o=('open', 'first'), c=('close', 'last'), h=('high', 'max'), l=('low', 'min'))
D1['chg'] = D1.c - D1.o
print('  TRAIN trend days (|open-close| > $90) and the grid on them:')
for dte, r in D1[D1.chg.abs() > 90].iterrows():
    k = H.dates.get_loc(dte)
    print(f'    {dte.date()} move {r.chg:+7.1f} range {r.h - r.l:6.1f}: grid day pnl {days.pnl.iloc[k]:+7.2f}, intraday min {days.intraday_min.iloc[k]:+8.1f}')
