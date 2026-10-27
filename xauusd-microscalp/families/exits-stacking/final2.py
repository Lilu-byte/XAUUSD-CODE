"""FINAL scoring (run once). Picks frozen from TRAIN-only work (stageA2, stageB2, daytarget2, gridscan2, mrscan2,
candidates2). TEST rows are used here for the first and only time.

A  MR_gated_bracket : signal = fade |close[i]-close[i-3]| > 3 x mean(high-low, last 240 M1 bars), only when the recorded
                      spread of bar i <= $0.10; enter at bar close; TP 0.75, SL 20, timeout 10 bars, max_open 1, cooldown 0.
C  MR_gated_stacked : same signal and bracket, max_open 5, cooldown 2 bars.
B  MR_grid          : basket direction = MR signal (no spread gate); add 0.01 lot each time the entry-side price moves
                      $2 against the last entry (max 50 positions); close all at combined +$0.30; no basket stop;
                      force-close at the session's last bar (22:58). FAIR 4-vertex in-bar path (5 seeds averaged).
"""
from sigs2 import *
from gridsim2 import *
import json

m1 = load_m1(); H = Harness(m1); S = build(m1)
mrg = gate(S['MR'], m1, 0.10); mr = S['MR']
te = m1.index >= SPLIT
pd.set_option('display.width', 250)
OUTJ = {}


def fmt(r):
    return (f'per_day {r["per_day"]:+6.2f} trades/day {r["trades_day"]:5.1f} win {r["win"]:.2f} pwin {r.get("pwin", np.nan):.2f} '
            f'per_trade {r["per_trade"]:+.3f} days>=5 {r["days_ge5"]:.2f} losing {r["losing_days"]:.2f} worst {r["worst_day"]:+7.1f} maxDD {r["max_dd"]:+7.1f}')


for name, sig, kw in (('A_MR_gated_bracket', mrg, dict(max_open=1, cooldown=0)),
                      ('C_MR_gated_stacked', mrg, dict(max_open=5, cooldown=2))):
    print(f'=== {name}: TP 0.75 SL 20 timeout 10 {kw}')
    res = {}
    d, t = run_pw(H, sig, 0.75, 20.0, timeout=10, **kw)
    res['train'] = summ(d, t, 'train'); res['test'] = summ(d, t, 'test')
    t.assign(day=t.entry.dt.normalize()).to_csv(OUT + f'final2_{name}_trades.csv', index=False)
    print('  TRAIN FAIR/base ', fmt(res['train']))
    print('  TEST  FAIR/base ', fmt(res['test']))
    for fill, sp in (('OHLC', 'base'), ('FAIR', 'bar'), ('FAIR', 'wide')):
        r = summ(*run_pw(H, sig, 0.75, 20.0, timeout=10, fill=fill, spread=sp, **kw), 'test'); res[f'test_{fill}_{sp}'] = r
        print(f'  TEST  {fill}/{sp:4s} ', fmt(r))
    rnd = [summ(*run_pw(H, random_like(sig, s), 0.75, 20.0, timeout=10, **kw), 'test')['per_day'] for s in range(20)]
    res['test_random_per_day'] = float(np.mean(rnd)); res['test_random_sd'] = float(np.std(rnd))
    print(f'  TEST random direction same bars (20 seeds): {np.mean(rnd):+.2f}/day (sd {np.std(rnd):.2f})')
    tt = t[t.entry >= SPLIT]
    print(f'  TEST avg holding {tt.bars.mean():.2f} bars, avg spread paid {tt.spr.mean():.3f}, kinds TP/SL/mixed/time '
          f'{(tt.kind == 0).mean():.2f}/{(tt.kind == 1).mean():.2f}/{(tt.kind == 2).mean():.2f}/{(tt.kind == 3).mean():.2f}')
    e = edge(m1, sig, horizons=(1, 2, 3, 5, 10)); print(e.round(3).to_string()); res['edge'] = e.round(4).to_dict()
    OUTJ[name] = res

print('\n=== B_MR_grid: step 2, max 50 positions, basket target +0.30, no stop, session-end close')
res = {}
G = []
for seed in range(5):
    days, bask, eqm, levm = run_grid(H, mr, 2.0, 50, 0.3, 0.0, tmax=0, seed=seed)
    G.append((days, bask, eqm, levm))
for per in ('train', 'test'):
    rr = pd.DataFrame([gsumm(H, *g, period=per) for g in G])
    res[per] = rr.mean(numeric_only=True).to_dict(); res[per + '_worst_seed'] = rr.min(numeric_only=True).to_dict()
    r = res[per]
    print(f'  {per.upper():5s} FAIR/base (5 seeds): per_day {r["per_day"]:+.2f} baskets/day {r["baskets_day"]:.1f} positions/day {r["positions_day"]:.1f} '
          f'per_position {r["per_position"]:+.3f} basket_win {r["basket_win"]:.3f} days>=5 {r["days_ge5"]:.2f} losing {r["losing_days"]:.2f} '
          f'worst_day {r["worst_day"]:+.1f} (worst seed {res[per + "_worst_seed"]["worst_day"]:+.1f}) worst_intraday {res[per + "_worst_seed"]["worst_intraday"]:+.1f} '
          f'max_dd_closed {r["max_dd_closed"]:+.1f} max_dd_float {res[per + "_worst_seed"]["max_dd_float"]:+.1f} max_levels {rr.max_levels.max():.0f} '
          f'stop-out 1:100 in {int(rr.stopout_1to100.sum())}/5 seeds, 1:500 in {int(rr.stopout_1to500.sum())}/5')
for path, sp in (('OHLC', 'base'), ('FAIR', 'bar'), ('FAIR', 'wide')):
    g = run_grid(H, mr, 2.0, 50, 0.3, 0.0, tmax=0, path=path, spread=sp)
    r = gsumm(H, *g, period='test'); res[f'test_{path}_{sp}'] = r
    print(f'  TEST  {path}/{sp:4s}: per_day {r["per_day"]:+.2f} per_position {r["per_position"]:+.3f} worst_day {r["worst_day"]:+.1f} '
          f'worst_intraday {r["worst_intraday"]:+.1f} max_dd_float {r["max_dd_float"]:+.1f} stop-out 1:100 {r["stopout_1to100"]} 1:500 {r["stopout_1to500"]}')
rg = pd.DataFrame([gsumm(H, *run_grid(H, random_like(mr, s), 2.0, 50, 0.3, 0.0, tmax=0, seed=s), period='test') for s in range(20)])
res['test_random_per_day'] = float(rg.per_day.mean()); res['test_random_sd'] = float(rg.per_day.std())
print(f'  TEST random direction baskets on the same MR bars (20 seeds): per_day {rg.per_day.mean():+.2f} (sd {rg.per_day.std():.2f}), '
      f'worst_day median {rg.worst_day.median():+.1f}, stop-outs at 1:100 {int(rg.stopout_1to100.sum())}/20')
days, bask, eqm, levm = G[0]
bt = bask[bask.start >= SPLIT]
print(f'  TEST basket depth (seed 0): {bt.levels.value_counts().sort_index().to_dict()}; mean basket duration {bt.bars.mean():.1f} bars; '
      f'force-closed at session end {(bt.why == 2).sum()} baskets, their pnl {bt.pnl[bt.why == 2].round(1).tolist()}')
e = edge(m1, mr, horizons=(1, 3, 5, 10, 30)); print(e.round(3).to_string()); res['edge'] = e.round(4).to_dict()
D1 = m1.groupby(m1.index.normalize()).agg(o=('open', 'first'), c=('close', 'last'), h=('high', 'max'), l=('low', 'min'))
D1['chg'] = D1.c - D1.o
print('  trend days (|open-close| > $90), grid seed 0..4 day pnl and worst intraday:')
for dte, r in D1[D1.chg.abs() > 90].iterrows():
    k = H.dates.get_loc(dte)
    print(f'    {dte.date()} {"TEST " if dte >= SPLIT else "TRAIN"} move {r.chg:+7.1f} range {r.h - r.l:6.1f}: day pnl '
          f'{[round(g[0].pnl.iloc[k], 1) for g in G]}, intraday min {[round(g[0].intraday_min.iloc[k], 0) for g in G]}')
# $3,000 account path over TEST (seed-by-seed): equity incl. floating, min margin level
for seed, g in enumerate(G):
    r = gsumm(H, *g, period='test')
    print(f'  seed {seed}: TEST total {r["total"]:+8.1f}, min equity vs TEST start {r["min_equity"]:+8.1f} -> $3,000 account low ${3000 + r["min_equity"]:,.0f}; '
          f'min margin level 1:100 {r["min_margin_level_1to100"]:.2f}, 1:500 {r["min_margin_level_1to500"]:.2f}')
gd = pd.DataFrame({f'seed{s}': g[0].pnl for s, g in enumerate(G)}); gd[gd.index >= SPLIT].to_csv(OUT + 'final2_B_MR_grid_testdays.csv')
OUTJ['B_MR_grid'] = res
json.dump(OUTJ, open(OUT + 'final2_results.json', 'w'), default=float, indent=1)
