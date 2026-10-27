"""Bar-by-bar copy of GoldAsiaBreak.mq5 v1.10 on the M5 export, and the side-by-side
result with GoldAllAgree's replay (xauusd-mt5/expected_trades_M5.csv).

What the EA does, and how it is modelled here (one 0.01 lot, $1 per $1):
- Range: today's M5 bars before 09:00; used only if there are at least 72 of them and
  the 08:55 bar exists, else no trade that day.
- Entry: the EA works on the first tick of each M5 bar (= that bar's open here). It
  trades only the FIRST closed bar outside the range, on the next bar's first tick:
  buy at ask (open + spread + slippage), sell at bid (open - slippage). Entries until
  22:29; if the first break can't be traded (spread, late bar), no trade that day.
- Exits: TP $5 / SL $50 from the modelled fill (the EA sets them from the quote it sends at,
  which is the fill in the Strategy Tester; with $0.10 slippage this copy is the cautious case),
  held on the broker's server (stop first if both
  fall inside one bar, gaps fill at the open); close at the 22:45 bar's open; a trade
  left from an earlier day (holiday early close) closes at the next session's first bar.
- Costs: spread $0.30 and $0.10 slippage (the report's base case), or the bar's recorded
  spread with --bar-spread; swap $0.126 (long) / $0.046 (short) a night, 3x into Thursday.
Usage: python3 -I asia_ea.py [--bar-spread]
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from lib import load, SWAP_LONG, SWAP_SHORT

SPREAD, SLIP, MAXSPR = 0.30, 0.10, 0.80
RANGE_END, CLOSE, LAST_ENTRY = 540, 22 * 60 + 45, 15
DAYS = pd.bdate_range('2025-05-06', '2026-10-09')

d = load('M5'); d = d[d.index.dayofweek < 5]
idx = d.index
o, h, l, c = (d[k].values for k in ('open', 'high', 'low', 'close'))
bar_spr = d.spread.values * 0.01
tod = (idx.hour * 60 + idx.minute).values
date = idx.normalize()
dkey = date.values

# Asian range per day: high, low, bar count, and whether the 08:55 bar exists
asia = d[tod < RANGE_END].assign(t=tod[tod < RANGE_END])
g = asia.groupby(asia.index.normalize())
R = pd.DataFrame({'hi': g.high.max(), 'lo': g.low.min(), 'n': g.size(), 'last': g.t.max()})
R['ok'] = (R.n >= 72) & (R['last'] == RANGE_END - 5)
rhi = R.hi.reindex(date).values; rlo = R.lo.reindex(date).values; rok = R.ok.reindex(date).fillna(False).values


def nights_swap(e, x, direction):
    n = pd.date_range(e.normalize(), x.normalize(), freq='D')[1:]
    return sum(3 if k.dayofweek == 3 else 1 for k in n) * (SWAP_LONG if direction == 1 else SWAP_SHORT)


def trades(tp=5.0, sl=50.0, bar_spread=False, direction=None):
    """direction: optional {date: +1/-1} to replace the breakout's direction (random baseline)."""
    sp = np.maximum(bar_spr, 0) if bar_spread else np.full(len(c), SPREAD)
    rows = []; pos = 0; done = None; first_seen = None
    for i in range(1, len(c)):
        day = dkey[i]
        if pos != 0:                                            # first tick of bar i
            ex = None
            stale = dkey[i] != dkey[ent_i]
            if pos == 1:
                if o[i] <= SLp: ex, px = 'SL', o[i] - SLIP
                elif o[i] >= TPp: ex, px = 'TP', o[i]
                elif tod[i] >= CLOSE or stale: ex, px = ('EOD' if not stale else 'next open'), o[i] - SLIP
            else:
                a = sp[i]
                if o[i] + a >= SLp: ex, px = 'SL', o[i] + a + SLIP
                elif o[i] + a <= TPp: ex, px = 'TP', o[i] + a
                elif tod[i] >= CLOSE or stale: ex, px = ('EOD' if not stale else 'next open'), o[i] + a + SLIP
            if ex:
                rows[-1].update(exit_time=idx[i], why=ex, exit_px=px); pos = 0
                continue                                        # the EA returns after a close on this tick
        if pos == 0 and done != day and RANGE_END < tod[i] < CLOSE - LAST_ENTRY and rok[i]:
            j = i - 1                                           # last closed bar
            if dkey[j] == day and tod[j] >= RANGE_END and first_seen != day:
                brk = c[j] > rhi[i] or c[j] < rlo[i]
                if brk:
                    first_seen = day; done = day                # only this bar's break may be traded today
                    on_time = (idx[i] - idx[j]) == pd.Timedelta(minutes=5)
                    dr = 1 if c[j] > rhi[i] else -1
                    if direction is not None: dr = direction[day]
                    if on_time and not (bar_spread and sp[i] > MAXSPR):
                        pos = dr; ent_i = i
                        if dr == 1: ent = o[i] + sp[i] + SLIP; SLp, TPp = ent - sl, ent + tp
                        else: ent = o[i] - SLIP; SLp, TPp = ent + sl, ent - tp
                        rows.append(dict(entry_time=idx[i], dir=dr, entry_px=ent))
        if pos != 0:                                            # rest of bar i: broker-side SL/TP
            a = sp[i]
            if pos == 1:
                if l[i] <= SLp: rows[-1].update(exit_time=idx[i] + pd.Timedelta(minutes=4), why='SL', exit_px=SLp - SLIP); pos = 0
                elif h[i] >= TPp: rows[-1].update(exit_time=idx[i] + pd.Timedelta(minutes=4), why='TP', exit_px=TPp); pos = 0
            else:
                if h[i] + a >= SLp: rows[-1].update(exit_time=idx[i] + pd.Timedelta(minutes=4), why='SL', exit_px=SLp + SLIP); pos = 0
                elif l[i] + a <= TPp: rows[-1].update(exit_time=idx[i] + pd.Timedelta(minutes=4), why='TP', exit_px=TPp); pos = 0
    if pos: rows.pop()
    t = pd.DataFrame(rows)
    t['gross'] = np.where(t.dir == 1, t.exit_px - t.entry_px, t.entry_px - t.exit_px)
    t['swap'] = [nights_swap(e, x, k) for e, x, k in zip(t.entry_time, t.exit_time, t.dir)]
    t['pnl'] = t.gross - t.swap
    return t


def per_day(t, col='pnl', when='exit_time'):
    return t.groupby(t[when].dt.normalize())[col].sum().reindex(DAYS, fill_value=0)


def stats(s):
    eq = s.cumsum(); m = s.groupby(s.index.to_period('M')).sum()
    return dict(per_day=round(s.mean(), 2), days_5=round((s >= 4.99).mean(), 2), losing_days=round((s < 0).mean(), 2),
                worst_day=round(s.min(), 0), worst_month=round(m.min(), 0), pos_months=round((m > 0).mean(), 2),
                max_dd=round((eq - eq.cummax()).min(), 0), total=round(s.sum(), 0))


if __name__ == '__main__':
    bar = '--bar-spread' in sys.argv
    e = pd.read_csv('/mnt/project-files/xauusd-mt5/expected_trades_M5.csv', parse_dates=['entry_time', 'exit_time'])
    ea = e.groupby(e.exit_time.dt.normalize()).pnl_usd.sum().reindex(DAYS, fill_value=0)
    print('costs:', 'bar spread + $0.10 slip' if bar else '$0.30 spread + $0.10 slip', '| days', len(DAYS))
    print('GoldAllAgree replay        ', stats(ea))
    for tp in (5, 8):
        t = trades(tp, 50, bar)
        t = t[(t.exit_time >= DAYS[0]) & (t.exit_time < DAYS[-1] + pd.Timedelta(days=1))]
        ab = per_day(t)
        print(f'--- TP ${tp}, stop $50: {len(t)} trades, wins {(t.pnl > 0).mean():.0%}, avg loss ${t.pnl[t.pnl < 0].mean():.1f}, '
              f'exits {t.why.value_counts().to_dict()}, swap ${t.swap.sum():.0f}')
        print('GoldAsiaBreak              ', stats(ab))
        print('both side by side          ', stats(ea + ab), '| daily corr', round(ea.corr(ab), 2))
        if tp == 5 and not bar:
            t.round({'entry_px': 2, 'exit_px': 2, 'gross': 2, 'swap': 2, 'pnl': 2}).to_csv('/mnt/project-files/xauusd-5-a-day/expected_trades_AsiaBreak.csv', index=False)
            rng = np.random.default_rng(0); nulls = []
            for seed in range(200):
                rr = np.random.default_rng(seed)
                dirs = {k: (1 if rr.random() < .5 else -1) for k in np.unique(dkey)}
                tn = trades(tp, 50, bar, dirs); tn = tn[(tn.exit_time >= DAYS[0]) & (tn.exit_time < DAYS[-1] + pd.Timedelta(days=1))]
                nulls.append(per_day(tn).mean())
            nulls = np.array(nulls)
            print(f'random direction, same entry bars (200 runs): median ${np.median(nulls):.2f}/day, 95th pct ${np.percentile(nulls, 95):.2f}, '
                  f'breakout beats {(nulls < ab.mean()).mean():.0%} of them')
