"""Lens (3): tail risk of P1 on a $3,000 account (0.01 lot = $1 per $1).
  (a) realised tails on the M1 data (whole file and TEST): worst day / trade / week, losing streaks, drawdown and its
      length, stop hits, P&L percentiles, the EA's $15 daily stop
  (b) the biggest real 1-minute moves in the file and what P1 did after them
  (c) synthetic news spikes ($20-40 one-minute moves, several shapes) injected into real quiet days at 15:30 server,
      with the stop filled at the $10 level and, pessimistically, at the worst price of the bar where it triggers,
      and with wider news spreads
  (d) how often 5-minute moves of $20+ happened in the M5/M15 history (how often such a test comes)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history')
from vlib import *

m = load_m1(); A = Arr(m)
s = p1_signal(m)
d, t = run(A, s)
ACC = 3000.0


def streak(x):
    best = cur = 0
    for v in x:
        cur = cur + 1 if v else 0; best = max(best, cur)
    return best


def tails(name, d, t):
    p = d.pnl; eq = p.cumsum(); dd = eq - eq.cummax()
    # drawdown length in trading days (from a peak to the recovery or the end)
    under = (dd < 0).values; dlen = streak(under)
    wk = p.groupby(p.index.to_period('W')).sum()
    q = np.percentile(t.pnl, [1, 5, 50, 95, 99])
    stops = t.pnl <= -9.999
    print(f'{name}: {len(p)} days, {len(t)} trades | worst day {p.min():+.1f} ({p.idxmin().date()}), worst trade {t.pnl.min():+.2f}, '
          f'worst week {wk.min():+.1f} ({wk.idxmin()}), best week {wk.max():+.1f} | longest losing-trade streak {streak((t.pnl < 0).values)}, '
          f'longest losing-day streak {streak((p < 0).values)} | max DD {dd.min():+.1f} (= {dd.min() / ACC * 100:+.1f}% of $3,000), '
          f'longest time under water {dlen} trading days')
    print(f'   trade P&L percentiles 1/5/50/95/99%: {q.round(2).tolist()}; trades <= -$5: {(t.pnl <= -5).sum()}; '
          f'$10 stop hits: {stops.sum()} ({stops.mean():.3f} of trades) costing {t.pnl[stops].sum():+.1f} in total, '
          f'while all other trades made {t.pnl[~stops].sum():+.1f}')
    print(f'   days below -$20: {(p < -20).sum()}, below -$30: {(p < -30).sum()}; one worst day = {abs(p.min()) / 5:.0f} days of the +$5 target')


tails('P1 whole M1 file (Jun 26 - Oct 9 2026)', d, t)
tails('P1 TEST (Sep 1 - Oct 9 2026)', d[d.index >= SPLIT], t[t.entry >= SPLIT])
# EA daily stop at -$15 (the EA's InpDailyLoss), verbatim logic of ea_replica.daily_stop
def daily_stop(T, limit=15.0):
    out = []
    for _, g in T.groupby(T.entry.dt.normalize()):
        cum = 0.0; hb = None
        for xi, pn in sorted(zip(g.xi, g.pnl)):
            cum += pn
            if cum <= -limit: hb = xi; break
        out.append(g if hb is None else g[g.ei < hb])
    return pd.concat(out)
T15 = daily_stop(t); d15 = T15.groupby(T15.entry.dt.normalize()).pnl.sum().reindex(A.dates, fill_value=0.0)
print(f'with the EA daily stop -$15: TRAIN {d15[d15.index < SPLIT].mean():+.2f}/day, TEST {d15[d15.index >= SPLIT].mean():+.2f}/day '
      f'(without: TRAIN {d.pnl[d.index < SPLIT].mean():+.2f}, TEST {d.pnl[d.index >= SPLIT].mean():+.2f}) -> the losses cluster on days that later recover')
# worst 5 days: what happened
r3 = (m.close - m.close.shift(3))
print('\nworst 5 days:')
for day, v in d.pnl.nsmallest(5).items():
    dm = m[m.index.normalize() == day]; tt = t[t.entry.dt.normalize() == day]
    print(f'  {day.date()} {v:+.1f}: {len(tt)} trades, {(tt.pnl <= -9.999).sum()} stops, long share {(tt.dir == 1).mean():.2f}; day range '
          f'${dm.high.max() - dm.low.min():.0f}, open->close {dm.close.iloc[-1] - dm.open.iloc[0]:+.0f}, biggest 1-min move '
          f'${dm.close.diff().abs().max():.1f}, biggest 3-min move ${r3[dm.index].abs().max():.1f}')
print('best 5 days: ' + ', '.join(f'{k.date()} {v:+.1f}' for k, v in d.pnl.nlargest(5).items()))

# ---------------------------------------------------------------- (b) biggest real 1-minute moves
r1 = m.close.diff()
gap = np.r_[0, np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64)]
r1 = r1.where(gap == 60)
print('\nlargest real 1-minute moves in the M1 file and P1 trades entered in the next 10 minutes:')
for ts, v in r1.abs().nlargest(10).items():
    i = m.index.get_loc(ts)
    tt = t[(t.ei >= i) & (t.ei <= i + 10)]
    after = m.close.iloc[min(i + 3, len(m) - 1)] - m.close.iloc[i]
    print(f'  {ts} move {r1[ts]:+6.1f}, next 3 min {after:+6.1f}, recorded spread on the bar ${m.spread_usd.iloc[i]:.2f}: '
          f'{len(tt)} P1 trades, P&L {tt.pnl.sum():+6.2f}, stops {(tt.pnl <= -9.999).sum()}')
nz = s != 0
print(f'recorded (minimum) spread: all bars median ${m.spread_usd.median():.2f}, P1 signal bars ${m.spread_usd[nz].median():.2f}, '
      f'bar after the signal ${m.spread_usd.shift(-1)[nz].median():.2f}; 90th pct on the bar after ${m.spread_usd.shift(-1)[nz].quantile(.9):.2f}')
print(f'M1 bars with |1-min move| > $10: {(r1.abs() > 10).sum()}, > $20: {(r1.abs() > 20).sum()} in {len(A.dates)} days')

# ---------------------------------------------------------------- (c) synthetic news spikes
SCEN = {
    'S1 runaway: +30 in 1 min, then +10 more over 3 min': [30, 34, 38, 40, 40, 40, 40, 40],
    'S2 spike then full reversal': [30, 15, 5, 0, 0, 0, 0, 0],
    'S3 staircase +8/min to +40': [8, 16, 24, 32, 40, 40, 40, 40],
    'S4 +40 then chop +-5': [40, 35, 42, 37, 41, 38, 40, 40],
    'S5 whipsaw +25 / -10 / +20': [25, -10, 20, 5, 15, 15, 15, 15],
    'S6 trend: +2.5 every minute for 30 min (+75)': list(np.arange(1, 31) * 2.5) + [75] * 5,
    'S7 +20 then +20 more in the next minute': [20, 40, 40, 40, 40, 40, 40, 40],
}


def inject(m, i0, path, spread):
    """Replace bars i0.. with a synthetic path (offsets from the close of bar i0-1); shift the rest of that day."""
    x = m.copy(); p0 = x.close.iloc[i0 - 1]
    o = x.open.values.copy(); h = x.high.values.copy(); l = x.low.values.copy(); c = x.close.values.copy(); sp = x.spread_usd.values.copy()
    day = x.index.normalize(); same = np.flatnonzero(day == day[i0])
    prev = p0
    for j, off in enumerate(path):
        k = i0 + j; cl = p0 + off
        o[k] = prev; c[k] = cl; h[k] = max(prev, cl) + 0.3; l[k] = min(prev, cl) - 0.3; sp[k] = spread; prev = cl
    rest = same[same >= i0 + len(path)]
    shift = (p0 + path[-1]) - x.open.values[rest[0]] if len(rest) else 0.0
    o[rest] += shift; h[rest] += shift; l[rest] += shift; c[rest] += shift
    sp[i0 + len(path): i0 + len(path) + 5] = spread
    x['open'], x['high'], x['low'], x['close'], x['spread_usd'] = o, h, l, c, sp
    return x


def slip_pnl(x, tt, sl=10.0, spr_add=0.05):
    """Re-price stopped trades pessimistically: the stop fills at the worst price of the bar where it triggers."""
    out = []
    H, L, O, C = x.high.values, x.low.values, x.open.values, x.close.values; sp = x.spread_usd.values + spr_add
    for r in tt.itertuples():
        i = r.ei; e = O[i + 1] + sp[i + 1] if r.dir == 1 else O[i + 1]
        pn = r.pnl
        if r.pnl <= -sl + 1e-6:
            j = r.xi
            pn = (L[j] - e) if r.dir == 1 else (e - (H[j] + sp[j]))
        out.append(pn)
    return np.array(out)


quiet = d.index[(d.index >= SPLIT)]
rng = np.random.default_rng(3)
days = [dd for dd in rng.choice(quiet, 8, replace=False)]
print('\nsynthetic news spikes injected at 15:30 server on 8 real TEST days (P1 trades with signal bar 15:27-15:50):')
for nm, path in SCEN.items():
    for spread in (0.30, 0.45):
        res = []; res_slip = []; ntr = []; nst = []
        for dd in days:
            ix = np.flatnonzero((m.index.normalize() == dd) & (m.tod.values == 15 * 60 + 30))
            if not len(ix): continue
            i0 = ix[0]; x = inject(m, i0, path, spread); Ax = Arr(x)
            dx, tx = run(Ax, p1_signal(x))
            tt = tx[(tx.ei >= i0 - 3) & (tx.ei <= i0 + len(path) + 15)]
            res.append(tt.pnl.sum()); res_slip.append(slip_pnl(x, tt).sum()); ntr.append(len(tt)); nst.append((tt.pnl <= -9.999).sum())
        print(f'  {nm:50s} spread ${spread:.2f}: event P&L mean {np.mean(res):+6.1f} (worst {np.min(res):+6.1f}); stop slipped to bar extreme: '
              f'mean {np.mean(res_slip):+6.1f} (worst {np.min(res_slip):+6.1f}); trades {np.mean(ntr):.1f}, stops {np.mean(nst):.1f}')

# ---------------------------------------------------------------- (d) how often a big test comes in history
for tf in ('M5', 'M15'):
    x = load_tf(tf)
    mv = (x.close - x.open).abs()
    g = pd.DataFrame({'ge20': (mv >= 20), 'ge40': (mv >= 40)}).groupby(x.index.year).sum()
    nd = pd.Series(x.index.normalize()).groupby(x.index.year).nunique()
    print(f'{tf} bars with |close-open| >= $20 / >= $40 per year (trading days): ' +
          ', '.join(f'{y}: {int(r.ge20)} / {int(r.ge40)} ({nd[y]}d)' for y, r in g.iterrows()))
