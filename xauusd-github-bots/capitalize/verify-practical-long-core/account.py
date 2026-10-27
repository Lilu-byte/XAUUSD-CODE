"""Account-level practicality: GoldAllAgree + GoldAsiaBreak + golden-cross core on one $3,000 hedging account,
May 2025..Oct 2026, marked to market on every M5 bar (not only at D1 closes).
- open lots (gross and net) over time, weekend exposure
- worst equity (intrabar: longs at the bar low, shorts at the bar high + spread), margin level at several leverages
- instant gap-down stress (5% and 10%) applied at every M5 bar: worst post-gap equity and margin level
- historical gaps and 1-day drops (D1 2004-2026, M5) to size the stress
- "started at a bad time" scenarios for the core alone
Usage: python3 -I account.py
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/verify-practical-long-core')
import numpy as np, pandas as pd
import gbt, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from core_stress import sim, D1, on as CORE_ON, dd

OUT = '/mnt/project-files/xauusd-github-bots/capitalize/verify-practical-long-core/'
M5 = gbt.load('M5'); SPR = 0.30
a = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
b = pd.read_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', parse_dates=['entry_time', 'exit_time'])
days = pd.DatetimeIndex(np.unique(M5.index.normalize()))

# ---------- core trades from my D1 simulator ----------
pc, heldc, tc = sim(CORE_ON)
tc = tc[tc.exit_time >= '2025-05-01'].copy()
# core exits at the D1 open = first M5 bar of that date; swap accrues nightly
pos = []   # (entry_ts, exit_ts, dir, entry_px, realized_pnl, swap_per_night)
for _, r in a.iterrows(): pos.append((r.entry_time, r.exit_time, 1, r.entry, r.pnl_usd, 'AA'))
for _, r in b.iterrows(): pos.append((r.entry_time, r.exit_time, int(r.dir), r.entry_px, r.pnl, 'AB'))
for _, r in tc.iterrows():
    et = r.exit_time
    xs = M5.index[M5.index.normalize() == et]
    x_ts = xs[0] if len(xs) else M5.index[-1]
    pos.append((r.entry_time, x_ts, 1, r.entry, r.pnl, 'CORE'))

idx = M5.index; n = len(idx)
lo, hi, cl = M5.low.values, M5.high.values, M5.close.values
dow = idx.dayofweek.values; dnorm = idx.normalize()
newday = np.r_[False, dnorm[1:] != dnorm[:-1]]
nights_mult = np.where(newday, np.where(np.r_[0, dow[:-1]] == 2, 3.0, 1.0), 0.0)
cum_nights = np.cumsum(nights_mult)

real = np.zeros(n)                       # realized P&L booked at exit bar
unr_c = np.zeros(n); unr_w = np.zeros(n)  # unrealized at close / worst intrabar
gross = np.zeros(n); net = np.zeros(n)
lots = {k: np.zeros(n) for k in ('AA', 'AB', 'CORE')}
for et, xt, dr, ep, rp, who in pos:
    i0 = idx.searchsorted(et); i1 = idx.searchsorted(xt)   # open from bar i0 to bar i1 (exit during/at i1)
    if i1 <= 0 or i0 >= n:
        # core entered before M5 data starts: open from the first bar
        pass
    i0 = max(i0, 0); i1 = min(i1, n - 1)
    if i1 < i0: continue
    sl_ = slice(i0, i1)   # bars fully held before the exit bar
    if dr == 1:
        unr_c[sl_] += cl[sl_] - ep; unr_w[sl_] += lo[sl_] - ep
    else:
        unr_c[sl_] += ep - (cl[sl_] + SPR); unr_w[sl_] += ep - (hi[sl_] + SPR)
    if who == 'CORE':   # accrued swap while open
        base = cum_nights[i0]
        acc = (cum_nights[sl_] - base) * 0.126
        unr_c[sl_] -= acc; unr_w[sl_] -= acc
    gross[sl_] += 1; net[sl_] += dr; lots[who][sl_] += 1
    real[i1] += rp
# core position open before the M5 window: its pre-window gain is in the starting equity (we start at $3,000
# with the core's open profit counted as zero at the first bar), so subtract the unrealized at bar 0 from everything
core_open0 = [p for p in pos if p[5] == 'CORE' and p[0] < idx[0]]
if core_open0:
    ep = core_open0[0][3]; xt = core_open0[0][1]; i1 = idx.searchsorted(xt)
    off = cl[0] - ep - (0 * 1.0)
    # rebase: equity counts only P&L made inside the window
    unr_c[:i1] -= off; unr_w[:i1] -= off
    # the realized P&L of that trade includes pre-window gains and pre-window swap: rebase it too
    pre_sw = sum(0.0 for _ in [])
    rp_full = core_open0[0][4]
    # realized booked = rp_full; the in-window part = rp_full - (cl[0] - ep) + accrued-swap-before-window (approx 0 here,
    # because the accrued swap counter starts at bar 0) -> book only in-window part
    real[i1] -= off + 0.0
    # pre-window swap was paid before the window: add it back (it is part of rp_full)
    tr_ = tc[tc.entry_time < idx[0]].iloc[0]
    sw_total = tr_.swap
    sw_in = (cum_nights[i1] - cum_nights[0]) * 0.126
    real[i1] += sw_total - sw_in

eq_c = 3000 + np.cumsum(real) + unr_c
eq_w = 3000 + np.cumsum(real) + unr_w
# same without the core
mask_core = lots['CORE'] > 0

print('=== Open lots, May 2025..Oct 2026, M5 bars ===')
for k in (1, 2, 3):
    print(f'  bars with >= {k / 100:.2f} lot open (gross): {(gross >= k).mean() * 100:5.1f}%   ({(gross >= k).sum()} bars)')
print('  max gross lots', gross.max() / 100, ' max net long lots', net.max() / 100, ' max net short', -net.min() / 100)
three = gross >= 3
if three.any():
    print('  first/last bar with 0.03 lot:', idx[three][0], idx[three][-1], ' distinct days:', len(np.unique(dnorm[three])))
# weekend exposure: lots held at the last bar of each Friday
fri_last = np.r_[dnorm[1:] != dnorm[:-1], True] & (dow == 4)
wk = gross[fri_last]
print(f'  weekends held: {len(wk)}; with 0.01 lot: {(wk == 1).sum()}, 0.02 lot: {(wk == 2).sum()}, 0.03 lot: {(wk == 3).sum()}, flat: {(wk == 0).sum()}')
print(f'  core-only weekends: {((lots["CORE"][fri_last] > 0) & (wk == 1)).sum()}, AA+core weekends: {((lots["CORE"][fri_last] > 0) & (lots["AA"][fri_last] > 0)).sum()}')

print('\n=== Equity on $3,000 (pair + core, intrabar worst, M5) ===')
i_min = eq_w.argmin()
print(f'  lowest equity ${eq_w.min():.0f} at {idx[i_min]} (gold {cl[i_min]:.0f}, lots open {gross[i_min] / 100:.2f}); end ${eq_c[-1]:.0f}')
e = pd.Series(eq_w, index=idx); pk = e.cummax(); ddm = (e - pk).min(); i_dd = (e - pk).values.argmin()
print(f'  worst peak-to-trough (intrabar) ${ddm:.0f}, trough {idx[i_dd]}, peak {e[:idx[i_dd]].idxmax()}')
# started at the worst moment: begin with $3,000 at the peak
e_tr = 3000 + ddm
print(f'  if David starts with $3,000 at that peak: equity at the trough ${e_tr:.0f} ({ddm / 3000 * 100:.0f}% of the account)')
# pair alone intrabar for comparison
pair_unr = unr_w.copy(); pair_real = real.copy()
# recompute pair-only quickly
real_p = np.zeros(n); unr_p = np.zeros(n)
for et, xt, dr, ep, rp, who in pos:
    if who == 'CORE': continue
    i0 = max(idx.searchsorted(et), 0); i1 = min(idx.searchsorted(xt), n - 1); sl_ = slice(i0, i1)
    unr_p[sl_] += (lo[sl_] - ep) if dr == 1 else (ep - (hi[sl_] + SPR)); real_p[i1] += rp
ep_ = pd.Series(3000 + np.cumsum(real_p) + unr_p, index=idx)
print(f'  pair alone: worst peak-to-trough intrabar ${(ep_ - ep_.cummax()).min():.0f}, lowest equity ${ep_.min():.0f}')

print('\n=== Margin level (equity / margin) ===')
rows = []
for lev in (20, 30, 50, 100, 500):
    mg_g = gross / 100 * 100 * cl / lev   # 0.01 lot = 1 oz -> gross lots*100 oz
    mg_g = gross * cl / lev
    with np.errstate(divide='ignore', invalid='ignore'):
        ml = np.where(mg_g > 0, eq_w / mg_g * 100, np.inf)
    r = dict(leverage=f'1:{lev}', min_margin_level_pct=round(ml.min(), 0), max_margin_used=round(mg_g.max(), 0))
    for gap in (0.05, 0.10):
        # instant gap down at bar close: longs lose gap*price per oz, shorts gain; AsiaBreak $50 SL and AA $100 stop
        # fill at the gapped price, so they do not cap the loss
        eq_g = eq_c - gap * cl * net
        mg_after = gross * cl * (1 - gap) / lev
        with np.errstate(divide='ignore', invalid='ignore'):
            mlg = np.where(gross > 0, eq_g / mg_after * 100, np.inf)
        r[f'gap{int(gap * 100)}_worst_equity'] = round(eq_g[gross > 0].min(), 0)
        r[f'gap{int(gap * 100)}_min_margin_level_pct'] = round(mlg.min(), 0)
        r[f'gap{int(gap * 100)}_bars_below_50pct'] = int((mlg < 50).sum())
        r[f'gap{int(gap * 100)}_bars_below_100pct'] = int((mlg < 100).sum())
    rows.append(r)
    print('  ', r)
pd.DataFrame(rows).to_csv(OUT + 'margin_stress.csv', index=False)
# the same, but a weekend gap (only positions open at Friday's last bar can be hit)
for gap in (0.05, 0.10):
    eq_g = (eq_c - gap * cl * net)[fri_last & (gross > 0)]
    print(f'  weekend gap {int(gap * 100)}%: worst equity after gap ${eq_g.min():.0f}; loss on the worst weekend ${(gap * cl * net)[fri_last].max():.0f}')
# worst equity if the gap hits exactly at the drawdown trough
for gap in (0.05, 0.10):
    j = i_dd
    print(f'  gap {int(gap * 100)}% at the drawdown trough ({idx[j]}, lots {gross[j] / 100:.2f}, net {net[j] / 100:.2f}): equity from a $3,000 start at the peak '
          f'${e_tr - gap * cl[j] * net[j]:.0f}')
# compounding the two: worst start + worst 3-lot moment + 10% gap
j3 = np.flatnonzero(gross >= 3)
if len(j3):
    eq3 = e.values[j3] - pk.values[j3]   # drawdown at those moments
    k = j3[eq3.argmin()]
    print(f'  deepest drawdown while 0.03 lot open: ${eq3.min():.0f} at {idx[k]}; + 10% gap on net {net[k] / 100:.2f} lot = ${eq3.min() - 0.10 * cl[k] * net[k]:.0f};'
          f' equity from a $3,000 start at the peak ${3000 + eq3.min() - 0.10 * cl[k] * net[k]:.0f}; margin level at 1:20 {(3000 + eq3.min() - 0.10 * cl[k] * net[k]) / (3 * cl[k] * 0.9 / 20) * 100:.0f}%')

print('\n=== How big are real gaps? ===')
d = D1.copy(); wd = d.index.dayofweek
prev_c = d.close.shift()
gap_all = (d.open / prev_c - 1)
mon = wd == 0
print(f'  D1 2004-2026: worst Monday open vs Friday close {gap_all[mon].min() * 100:.1f}% on {gap_all[mon].idxmin().date()}; worst any open gap {gap_all.min() * 100:.1f}% on {gap_all.idxmin().date()}')
print('  5 worst weekend gaps %:', (gap_all[mon].nsmallest(5) * 100).round(1).to_dict())
r1 = d.close / prev_c - 1
print(f'  worst close-to-close day {r1.min() * 100:.1f}% on {r1.idxmin().date()}; worst open-to-low intraday {((d.low / prev_c - 1).min()) * 100:.1f}% on {(d.low / prev_c - 1).idxmin().date()}')
print('  days with close-to-close <= -5% since 2004:', int((r1 <= -0.05).sum()), {k.date(): round(v * 100, 1) for k, v in r1[r1 <= -0.05].items()})
# 30 Jan 2026 detail: what was open
dd30 = pd.Timestamp('2026-01-30')
mk = dnorm == dd30
if mk.any():
    print(f'  30 Jan 2026: max gross lots that day {gross[mk].max() / 100:.2f}; lots at day start {gross[mk][0] / 100:.2f}; equity change that day (close basis) ${eq_c[mk][-1] - eq_c[np.flatnonzero(mk)[0] - 1]:.0f}; '
          f'gold {cl[np.flatnonzero(mk)[0] - 1]:.0f} -> low {lo[mk].min():.0f} -> close {cl[mk][-1]:.0f}')

print('\n=== Core alone: started on a bad day (D1, 2016-2026, any day the rule is long) ===')
# if David switches the EA on while the rule is long, it buys at the next open and holds to the rule's exit
c = D1.close.values; o = D1.open.values; low = D1.low.values; on = CORE_ON
res = []
for s in range(len(D1) - 1):
    if D1.index[s] < pd.Timestamp('2016-01-01') or not on[s]: continue
    j = s + 1; ent = o[j] + 0.4; worst = 0.0; nights = 0.0
    while j < len(D1) and on[j - 1]:
        if j > s + 1: nights += 3 if D1.index[j - 1].dayofweek == 2 else 1
        worst = min(worst, low[j] - ent - nights * 0.126)
        j += 1
    xp = o[j] - 0.1 if j < len(D1) else c[-1]
    res.append((D1.index[s], ent, worst, xp - ent - nights * 0.126))
r = pd.DataFrame(res, columns=['start', 'entry', 'worst_open_loss', 'final'])
k = r.worst_open_loss.idxmin()
print(f'  worst open loss for a late starter: ${r.worst_open_loss.min():.0f} (switched on {r.start[k].date()}, bought ~{r.entry[k]:.0f}), final result of that start ${r.final[k]:.0f}')
print(f'  starts that ended in a loss: {(r.final < 0).mean() * 100:.0f}% of {len(r)} possible start days; worst final ${r.final.min():.0f} (start {r.start[r.final.idxmin()].date()})')
print(f'  starts with an open loss worse than -$1,000: {(r.worst_open_loss < -1000).mean() * 100:.0f}%; worse than -$1,500: {(r.worst_open_loss < -1500).mean() * 100:.0f}%')
