"""Shared scoring for "trade more often without compromise" (17 Oct 2026).

Question (David, 17 Oct 14:20 UTC): "any way to have it trade more often without compromise?"
"It" = the pair GoldAllAgree v1.10 + GoldAsiaBreak v1.10 (one 0.01 lot each, $1 per $1 move).
"Without compromise" (default): with the extra trades, the pair's $ a day must not fall and its
worst drawdown must not deepen, on the pair's own window AND on older data it wasn't tuned on.

What is here (all one 0.01 lot, $ per day = P&L booked on the exit day, Mon-Fri):
- allagree(): GoldAllAgree's rule on any base timeline, with variants (EMAs, timeframes, how many
  must agree, long or short side). Defaults reproduce xauusd-mt5/expected_trades_M5.csv.
- asia(): GoldAsiaBreak v1.10 on any base timeline (M5, M15, H1). Defaults on M5 reproduce
  xauusd-5-a-day/code/asia_ea.py (the EA's line-by-line copy) trade for trade.
- per_day(), mtm_daily(), score(): daily P&L, mark-to-market daily equity and the summary.
- WINDOWS: where each test lives. M5 data starts May 2025, M15 mid-2022, H1 mid-2016.
  'pair' = the pair's own window (May 6 2025 - Oct 9 2026, M5) - every number David has seen.
  'm15_train' = Jul 11 2022 - Jun 28 2024 (M15)  -> choose settings here.
  'm15_test'  = Jul 1 2024 - Oct 9 2026 (M15)    -> score once.
  'h1_old'    = Aug 1 2016 - Jun 30 2022 (H1)    -> older-data sanity check (entries up to an hour late).
Costs: spread $0.30 + slippage $0.10 for GoldAsiaBreak-style orders (as the EA copy), the bar's
recorded spread at entry/exit for GoldAllAgree (as its replay), swap $0.126 long / $0.046 short a
night, triple into Thursday. On M15/H1 the dollar distances can be scaled to today's price
(scale=True: x price/4000) so a "$5 target" is the same percentage move in 2017 as in 2026.

Usage from another script:
    import sys; sys.dont_write_bytecode = True
    sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/code'); import harness as H
    base = H.pair_parts('pair')                       # {'AllAgree': trades, 'AsiaBreak': trades}
    print(H.score(base, 'pair'))
    print(H.score({**base, 'MyIdea': my_trades}, 'pair'))
A trades DataFrame needs: entry_time, exit_time, dir (+1/-1), entry_px, exit_px, pnl ($, after costs).
"""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from lib import load as _load, ema, align, MIN, SWAP_LONG, SWAP_SHORT

SPREAD, SLIP, REF = 0.30, 0.10, 4000.0
WINDOWS = {
    'pair':      ('M5',  '2025-05-06', '2026-10-09'),
    'm15_train': ('M15', '2022-07-11', '2024-06-28'),
    'm15_test':  ('M15', '2024-07-01', '2026-10-09'),
    'm15_all':   ('M15', '2022-07-11', '2026-10-09'),
    'h1_old':    ('H1',  '2016-08-01', '2022-06-30'),
}
_cache = {}


def load(tf):
    if tf not in _cache:
        d = _load(tf)
        _cache[tf] = d[d.index.dayofweek < 5]
    return _cache[tf]


def days(window):
    tf, a, b = WINDOWS[window]
    return pd.bdate_range(a, b)


def nights_swap(e, x, direction):
    n = pd.date_range(pd.Timestamp(e).normalize(), pd.Timestamp(x).normalize(), freq='D')[1:]
    return sum(3 if k.dayofweek == 3 else 1 for k in n) * (SWAP_LONG if direction == 1 else SWAP_SHORT)


# ---------------------------------------------------------------- GoldAllAgree
def trend_matrix(base='M5', tfs=('M5', 'M15', 'M30', 'H1', 'H4'), fast=20, slow=80):
    """Sign of EMA(fast) - EMA(slow) on each timeframe, known at each base-bar close (rows = tfs)."""
    b = load(base) if base != 'M5' else _load('M5')
    bc = b.index + pd.Timedelta(minutes=MIN[base])
    T = []
    for tf in tfs:
        d = _load(tf)
        T.append(align(d, tf, bc, np.sign(ema(d.close, fast) - ema(d.close, slow)).values).fillna(0).values)
    return b, bc, np.vstack(T)


def allagree(base='M5', tfs=('M5', 'M15', 'M30', 'H1', 'H4'), fast=20, slow=80, need=None, side=1, on=None):
    """GoldAllAgree's replay: in while at least `need` (default all) of `tfs` point `side` way at a
    base-bar close; out at the first close where that stops. Long buys at ask (close + recorded
    spread) and sells at the bid close; short sells at the bid close and buys back at ask.
    `on` may pass a ready boolean array (one per base bar) instead of the EMA rule."""
    b, bc, S = trend_matrix(base, tfs, fast, slow)
    if on is None:
        k = len(tfs) if need is None else need
        on = ((S > 0) if side == 1 else (S < 0)).sum(0) >= k
    pos = pd.Series(np.asarray(on).astype(int), index=bc)
    px = pd.Series(b.close.values, index=bc); spr = pd.Series(b.spread.values * 0.01, index=bc)
    chg = pos.diff().fillna(pos)
    rows = []; entry = None
    for t, c in chg[chg != 0].items():
        if c > 0:
            entry = (t, px[t] + spr[t] if side == 1 else px[t])
        elif entry:
            xp = px[t] if side == 1 else px[t] + spr[t]
            sw = nights_swap(entry[0], t, side)
            g = (xp - entry[1]) * side
            rows.append(dict(entry_time=entry[0], exit_time=t, dir=side, entry_px=entry[1], exit_px=xp,
                             gross=g, swap=sw, pnl=g - sw))
            entry = None
    return pd.DataFrame(rows, columns=['entry_time', 'exit_time', 'dir', 'entry_px', 'exit_px', 'gross', 'swap', 'pnl'])


# ---------------------------------------------------------------- GoldAsiaBreak
def asia(tf='M5', tp=5.0, sl=50.0, scale=False, range_end=540, close=22 * 60 + 45, last_entry=15,
         min_bars=None, bar_spread=False, direction=None, maxspr=0.80, spread=SPREAD, slip=SLIP):
    """GoldAsiaBreak v1.10 on any base timeline (copy of asia_ea.trades generalised).
    Range = today's bars before range_end (server minutes); needs min_bars of them and the bar that
    ends at range_end. Trades only the FIRST closed bar outside the range, on the next bar's open,
    TP/SL from the fill, broker-side (stop first if both in one bar), close at the `close` bar's open,
    a trade left from an earlier day closes at the next open. scale=True multiplies $ distances and
    costs by price/4000 and reports P&L in today's dollars."""
    d = load(tf)
    m = MIN[tf]
    if min_bars is None: min_bars = int(round(range_end / m * 2 / 3))   # 72 of 108 M5 bars, as the EA
    idx = d.index
    o, h, l, c = (d[k].values for k in ('open', 'high', 'low', 'close'))
    bar_spr = d.spread.values * 0.01
    tod = (idx.hour * 60 + idx.minute).values
    date = idx.normalize(); dkey = date.values
    sc = (c / REF) if scale else np.ones(len(c))
    a_ = d[tod < range_end].assign(t=tod[tod < range_end])
    g = a_.groupby(a_.index.normalize())
    R = pd.DataFrame({'hi': g.high.max(), 'lo': g.low.min(), 'n': g.size(), 'last': g.t.max()})
    R['ok'] = (R.n >= min_bars) & (R['last'] == range_end - m)
    rhi = R.hi.reindex(date).values; rlo = R.lo.reindex(date).values; rok = R.ok.reindex(date).fillna(False).values
    sp = np.maximum(bar_spr, 0) if bar_spread else np.full(len(c), spread)
    rows = []; pos = 0; done = None; first_seen = None; ent_i = 0; e_sc = 1.0
    bar = pd.Timedelta(minutes=m); inbar = pd.Timedelta(minutes=m - 1)
    for i in range(1, len(c)):
        day = dkey[i]
        if pos != 0:
            ex = None; s_ = slip * e_sc; a = sp[i] * e_sc
            stale = dkey[i] != dkey[ent_i]
            if pos == 1:
                if o[i] <= SLp: ex, px = 'SL', o[i] - s_
                elif o[i] >= TPp: ex, px = 'TP', o[i]
                elif tod[i] >= close or stale: ex, px = ('EOD' if not stale else 'next open'), o[i] - s_
            else:
                if o[i] + a >= SLp: ex, px = 'SL', o[i] + a + s_
                elif o[i] + a <= TPp: ex, px = 'TP', o[i] + a
                elif tod[i] >= close or stale: ex, px = ('EOD' if not stale else 'next open'), o[i] + a + s_
            if ex:
                rows[-1].update(exit_time=idx[i], why=ex, exit_px=px); pos = 0
                continue
        if pos == 0 and done != day and range_end < tod[i] < close - last_entry and rok[i]:
            j = i - 1
            if dkey[j] == day and tod[j] >= range_end and first_seen != day:
                if c[j] > rhi[i] or c[j] < rlo[i]:
                    first_seen = day; done = day
                    on_time = (idx[i] - idx[j]) == bar
                    dr = 1 if c[j] > rhi[i] else -1
                    if direction is not None: dr = direction[day]
                    if on_time and not (bar_spread and sp[i] > maxspr):
                        pos = dr; ent_i = i; e_sc = sc[i]; s_ = slip * e_sc
                        if dr == 1: ent = o[i] + sp[i] * e_sc + s_; SLp, TPp = ent - sl * e_sc, ent + tp * e_sc
                        else: ent = o[i] - s_; SLp, TPp = ent + sl * e_sc, ent - tp * e_sc
                        rows.append(dict(entry_time=idx[i], dir=dr, entry_px=ent, sc=e_sc))
        if pos != 0:
            a = sp[i] * e_sc; s_ = slip * e_sc
            if pos == 1:
                if l[i] <= SLp: rows[-1].update(exit_time=idx[i] + inbar, why='SL', exit_px=SLp - s_); pos = 0
                elif h[i] >= TPp: rows[-1].update(exit_time=idx[i] + inbar, why='TP', exit_px=TPp); pos = 0
            else:
                if h[i] + a >= SLp: rows[-1].update(exit_time=idx[i] + inbar, why='SL', exit_px=SLp + s_); pos = 0
                elif l[i] + a <= TPp: rows[-1].update(exit_time=idx[i] + inbar, why='TP', exit_px=TPp); pos = 0
    if pos: rows.pop()
    t = pd.DataFrame(rows)
    t['gross'] = np.where(t.dir == 1, t.exit_px - t.entry_px, t.entry_px - t.exit_px) / t.sc
    t['swap'] = [nights_swap(e, x, k) for e, x, k in zip(t.entry_time, t.exit_time, t.dir)]
    t['pnl'] = t.gross - t.swap
    return t


# ---------------------------------------------------------------- the pair, per window
def pair_parts(window='pair', scale=True):
    """The two EAs as they run, on the window's base timeline. On M15/H1 GoldAllAgree can't use
    its M5 trend, so it runs as its 'Use M5 = off' version (M15, M30, H1, H4); asia() runs on
    that timeline with scaled $ distances (scale applies to M15/H1 only)."""
    tf = WINDOWS[window][0]
    if tf == 'M5':
        return {'AllAgree': allagree('M5'), 'AsiaBreak': asia('M5')}
    tfs = ('M15', 'M30', 'H1', 'H4') if tf == 'M15' else ('H1', 'H4')
    aa = allagree(tf, tfs)
    if scale:   # GoldAllAgree is one 0.01 lot whatever the price; report in today's dollars too
        sc = aa.entry_px / REF
        aa = aa.assign(sc=sc, pnl=aa.pnl / sc, gross=aa.gross / sc, swap=aa.swap / sc)
    return {'AllAgree': aa, 'AsiaBreak': asia(tf, scale=scale)}


# ---------------------------------------------------------------- scoring
def in_window(t, window):
    D = days(window)
    return t[(t.exit_time >= D[0]) & (t.exit_time < D[-1] + pd.Timedelta(days=1))]


def per_day(t, window):
    D = days(window)
    t = in_window(t, window)
    return t.groupby(t.exit_time.dt.normalize()).pnl.sum().reindex(D, fill_value=0.0)


def mtm_daily(t, window):
    """End-of-day equity change counting open trades at each day's last close (bid; shorts at
    bid + recorded spread), so a trade held for days shows its drawdown while it is open."""
    tf = WINDOWS[window][0]
    D = days(window)
    d = load(tf)
    last = d.groupby(d.index.normalize()).agg(c=('close', 'last'), s=('spread', 'last')).reindex(D).ffill()
    eq = pd.Series(0.0, index=D)
    for r in in_window(t, window).itertuples():
        e_day = pd.Timestamp(r.entry_time).normalize(); x_day = pd.Timestamp(r.exit_time).normalize()
        sc = getattr(r, 'sc', 1.0)
        sc = 1.0 if not np.isfinite(sc) else sc
        for k in D[(D >= e_day) & (D < x_day)]:
            px = last.c[k] if r.dir == 1 else last.c[k] + last.s[k] * 0.01
            eq[k] += (px - r.entry_px) * r.dir / sc
    # eq now holds unrealized P&L at each day's end; add realized P&L cumulatively
    real = per_day(t, window).cumsum()
    return real + eq   # equity (not daily change)


def score(parts, window='pair', mtm=True, by_period=True):
    """Combined daily stats for a dict of trade lists (or a single DataFrame)."""
    if isinstance(parts, pd.DataFrame): parts = {'x': parts}
    D = days(window)
    daily = sum(per_day(t, window) for t in parts.values())
    ntr = sum(len(in_window(t, window)) for t in parts.values())
    eq = daily.cumsum(); m = daily.groupby(daily.index.to_period('M')).sum()
    out = dict(per_day=round(daily.mean(), 2), trades_day=round(ntr / len(D), 2),
               days_traded=round(np.mean(sum((per_day(t, window) != 0).astype(int) for t in parts.values()) > 0), 2),
               days_5=round((daily >= 4.99).mean(), 2), losing_days=round((daily < 0).mean(), 2),
               worst_day=round(daily.min(), 0), worst_month=round(m.min(), 0), pos_months=round((m > 0).mean(), 2),
               max_dd=round((eq - eq.cummax()).min(), 0))
    if mtm:
        q = sum(mtm_daily(t, window) for t in parts.values())
        out['max_dd_mtm'] = round((q - q.cummax()).min(), 0)
    out['total'] = round(daily.sum(), 0)
    if by_period and window == 'pair':
        y = daily.groupby(daily.index.year).mean()
        out['per_day_2025'] = round(y.get(2025, np.nan), 2); out['per_day_2026'] = round(y.get(2026, np.nan), 2)
    if by_period and window != 'pair':
        y = daily.groupby(daily.index.year).mean().round(2)
        out['per_day_by_year'] = y.to_dict()
    return out


def corr(a, b, window='pair'):
    return round(per_day(a, window).corr(per_day(b, window)), 2)


if __name__ == '__main__':
    pd.set_option('display.width', 220)
    for w in ('pair', 'm15_train', 'm15_test', 'h1_old'):
        P = pair_parts(w)
        print(w, {k: len(in_window(v, w)) for k, v in P.items()})
        for k, v in P.items(): print('   ', k, score(v, w))
        print('    PAIR', score(P, w))
