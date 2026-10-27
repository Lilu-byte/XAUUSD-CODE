"""(1) reproduce pick C from the rule text, (2) 50 random-direction seeds, (3) costs / fills / latency / spread filter,
(5) concentration. Output summary only."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/repro')
from vlib import *
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from ea_sim import _sim_next

NCONF = 0
def run(d, s, spr, **kw):
    global NCONF; NCONF += 1
    return trades(d, s, spr, **kw)

def line(name, T, dates, extra=0.0):
    a = stats(T, dates, *TRAIN, extra); b = stats(T, dates, *TEST, extra)
    print(f"{name:42s} TRAIN {a['per_day']:+.3f}/d {a['trades_day']:.3f}t {a['per_trade']:+.3f}/tr | "
          f"TEST {b['per_day']:+.3f}/d {b['trades_day']:.3f}t {b['per_trade']:+.3f}/tr")
    return a, b

for zf in ('hour', 'month_hour'):
    d = load(M15_FILE, 15, zf)
    dates = pd.DatetimeIndex(np.unique(d.date.values))
    s, ar, vw, mv = signal(d)
    base = d.spr_bar.values + 0.05
    T = run(d, s, base)
    print(f'\n=== zero-spread fill = {zf}; signals {int((s != 0).sum())}, eligible trades {len(T)}')
    a, b = line('base FAIR (pick C)', T, dates)
    if zf != 'month_hour':
        continue
    # ---- cross-check vs ea_sim._sim_next with the same arrays
    el = eligible(d)
    day = np.unique(d.date.values, return_inverse=True)[1].astype(np.int64)
    sg = np.where(el, s, 0).astype(np.int64)
    dp, dt, ti, to, tpn, tdr = _sim_next(d.open.values, d.high.values, d.low.values, d.close.values, base,
                                         d.tod.values.astype(np.int64), day, d.last.values.astype(np.bool_), sg,
                                         1000.0, 25.0, 2, 3, 1, 0.0, 0.0, 0)
    Ts = pd.DataFrame({'i': ti, 'pnl': tpn, 'dir': tdr})
    mm = T.merge(Ts, on='i', how='outer', suffixes=('', '_s'))
    print(f'  cross-check vs _sim_next: trades mine {len(T)} sim {len(Ts)}, max |pnl diff| {np.nanmax(np.abs(mm.pnl - mm.pnl_s)):.2e}, '
          f'unmatched {int(mm.pnl.isna().sum() + mm.pnl_s.isna().sum())}')
    T1 = run(d, s, base)  # mo=1 check: how often a 2nd position overlaps
    ov = np.sum(np.diff(T.i.values) == 1)
    print(f'  overlapping (consecutive-bar) entries: {ov} of {len(T)}; exit kinds: {T.kind.value_counts().to_dict()}')
    # ---- full stats
    for nm, (lo, hi) in (('TRAIN', TRAIN), ('TEST', TEST), ('M1ERA', ('2026-06-26', '2026-10-10')),
                         ('TEST_pre_M1', ('2025-01-01', '2026-06-26'))):
        st = stats(T, dates, lo, hi)
        print(f"  {nm:11s} {st['per_day']:+.3f}/d {st['trades_day']:.3f} tr/d win {st['win']:.3f} {st['per_trade']:+.3f}/tr "
              f"days>=5 {st['days_ge5']:.3f} losing {st['losing_days']:.3f} worst day {st['worst_day']:+.2f} worst tr {st['worst_trade']:+.2f} "
              f"maxDD {st['max_dd']:+.1f} long share {st['long_share']:.3f} trades {st['trades']} days {st['days']} t {st['t_trade']:+.2f} "
              f"breakeven extra cost/tr {st['per_trade']:+.3f}")
    # ---- random, always long / short
    R = []
    for z in range(50):
        r = np.where(np.random.default_rng(1000 + z).random(len(s)) < .5, 1, -1)
        Tr = run(d, np.where(s != 0, r, 0), base)
        R.append((stats(Tr, dates, *TRAIN)['per_day'], stats(Tr, dates, *TEST)['per_day']))
    R = np.array(R)
    print(f'  random 50 seeds: TRAIN mean {R[:, 0].mean():+.3f} sd {R[:, 0].std():.3f} max {R[:, 0].max():+.3f} share >= pick {(R[:, 0] >= a["per_day"]).mean():.2f} | '
          f'TEST mean {R[:, 1].mean():+.3f} sd {R[:, 1].std():.3f} max {R[:, 1].max():+.3f} share >= pick {(R[:, 1] >= b["per_day"]).mean():.2f}')
    print(f'  z-score vs random: TRAIN {(a["per_day"] - R[:, 0].mean()) / R[:, 0].std():+.2f}, TEST {(b["per_day"] - R[:, 1].mean()) / R[:, 1].std():+.2f}')
    line('  always long same bars', run(d, np.where(s != 0, 1, 0), base), dates)
    line('  always short same bars', run(d, np.where(s != 0, -1, 0), base), dates)
    # ---- costs
    print('  --- costs / fills / latency')
    line('  bar spread', run(d, s, d.spr_bar.values), dates)
    line('  base + $0.07 commission', T, dates, extra=0.07)
    line('  flat $0.30', run(d, s, np.full(len(d), 0.30)), dates)
    line('  flat $0.40', run(d, s, np.full(len(d), 0.40)), dates)
    line('  base + $0.08 (M1 first-minute bias)', run(d, s, base + 0.08), dates)
    line('  base, fills FAIR=OHLC=STOP (no TP)', T, dates)
    line('  base, stop filled at bar extreme', run(d, s, base, stop_fill='extreme'), dates)
    line('  latency 1 bar (15 min)', run(d, s, base, latency=1), dates)
    line('  latency 2 bars (30 min)', run(d, s, base, latency=2), dates)
    line('  entry only if next-bar spread < $0.30', run(d, s, base, elig=eligible(d, 0.2999)), dates)
    line('  entry only if next-bar spread < $0.20', run(d, s, base, elig=eligible(d, 0.1999)), dates)
    # ---- neighbours (rule perturbations, same family)
    print('  --- neighbours')
    for kk in (3.0, 3.5, 4.5, 5.0):
        line(f'  k={kk}', run(d, signal(d, k=kk)[0], base), dates)
    for NN in (1, 3, 4):
        line(f'  hold N={NN}', run(d, s, base, N=NN), dates)
    for ss in (10.0, 15.0, 40.0, 1000.0):
        line(f'  stop {ss}', run(d, s, base, sl=ss), dates)
    line('  no VWAP gate', run(d, signal(d, gate=False)[0], base), dates)
    for LL in (24, 48):
        line(f'  AR length {LL}', run(d, signal(d, L=LL)[0], base), dates)
    # ---- concentration
    print('  --- concentration (base)')
    for nm, (lo, hi) in (('TRAIN', TRAIN), ('TEST', TEST), ('ALL', ('2022-07-01', '2026-10-10'))):
        t = T[(T.entry >= lo) & (T.entry < hi)]
        p = t.groupby(t.entry.dt.normalize()).pnl.sum().sort_values(ascending=False)
        tot = p.sum(); top5 = p.head(5).sum(); ndays_all = len(dates[(dates >= lo) & (dates < hi)])
        lt = t[t.dir == 1].pnl; sh = t[t.dir == -1].pnl
        tt = t.pnl.sort_values(ascending=False)
        print(f"  {nm}: total ${tot:+.1f} over {len(p)} trading-active days; top-5 days ${top5:+.1f} = {top5 / tot:.0%} of total; "
              f"without top 5 days {(tot - top5) / ndays_all:+.3f}/d; top-5 trades ${tt.head(5).sum():+.1f}; without top 10 trades "
              f"{(tot - tt.head(10).sum()) / ndays_all:+.3f}/d | long {len(lt)} tr ${lt.sum():+.1f} ({lt.mean():+.2f}/tr), short {len(sh)} tr ${sh.sum():+.1f} ({sh.mean():+.2f}/tr)")
    y = T.groupby(T.entry.dt.year).pnl.agg(['size', 'sum', 'mean'])
    print('  by year [trades, $total, $/tr]: ' + '; '.join(f'{i} [{int(r["size"])}, {r["sum"]:+.1f}, {r["mean"]:+.2f}]' for i, r in y.iterrows()))
    # bootstrap of per-day mean (days resampled), TRAIN and TEST
    rng = np.random.default_rng(5)
    for nm, (lo, hi) in (('TRAIN', TRAIN), ('TEST', TEST)):
        p = per_day(T, dates); p = p[(p.index >= lo) & (p.index < hi)].values
        bs = np.array([rng.choice(p, len(p)).mean() for _ in range(5000)])
        print(f'  bootstrap {nm} $/day: mean {p.mean():+.3f}, 90% CI [{np.quantile(bs, .05):+.3f}, {np.quantile(bs, .95):+.3f}], P(<=0) {(bs <= 0).mean():.3f}')
    T.to_csv('/mnt/project-files/xauusd-microscalp/verify/snapback-history/repro/pickC_trades.csv', index=False)
print(f'\nconfigurations simulated in this script (incl. random seeds, cost/latency variants, neighbours): {NCONF}')
