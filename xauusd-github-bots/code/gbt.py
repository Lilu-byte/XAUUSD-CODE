"""Shared bar-by-bar backtester for the GitHub bot rebuilds (one 0.01 lot of XAUUSD, $1 per $1 move).

Prices are MT5 bid candles from David's export (server time GMT+2/+3).
A signal decided on a closed bar i is filled at the open of bar i+1:
long buys at ask (bid + spread) + slippage, short sells at bid - slippage.
Long exits at bid, short exits at ask. Take-profit is a limit (no slippage);
stops fill at the level, or at the open if price gapped through, minus slippage.
If the stop and the target are both inside one bar, the STOP is assumed (conservative).
After a stop or target is hit inside a bar, no new trade can open at that same bar's open (fixed 17 Oct 2026;
before that the engine could re-enter at an open that came earlier in time than the stop).
Breakeven and trailing stops are updated from a bar's high/low only after that bar
is checked for exits, so they act from the next bar.
A trade still open on the last bar is NOT returned by simulate(); append a closing bar when that matters
(noted 17 Oct 2026 by the Market Matrix checks; at most one trade per bot, so earlier results are unaffected in practice).
Costs: flat spread $0.30 + $0.10 slippage (project convention, same as the
GoldAllAgree + GoldAsiaBreak replay), swap $0.126 long / $0.046 short per night,
triple on Wednesday night.
"""
import numpy as np, pandas as pd
from numba import njit

D = '/mnt/project-files/'
FILES = {'M1': D + 'xauusd-microscalp/data/XAUUSD_M1.csv',
         'M5': D + 'xauusd-intraday/data/XAUUSD_M5.csv',
         'M15': D + 'xauusd-intraday/data/XAUUSD_M15.csv',
         'H1': D + 'xauusd-price-action/data/XAUUSD_H1.csv',
         'H4': D + 'xauusd-price-action/data/XAUUSD_H4.csv',
         'D1': D + 'xauusd-price-action/data/XAUUSD_D1.csv'}
SPREAD, SLIP = 0.30, 0.10
SWAP_L, SWAP_S = 0.126, 0.046
_cache = {}


def load(tf):
    if tf in _cache:
        return _cache[tf]
    if tf == 'M30':
        m = load('M15')
        g = m.resample('30min', label='left', closed='left')
        d = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(),
                          'close': g.close.last(), 'spread': g.spread.mean(), 'vol': g.vol.sum()}).dropna()
    else:
        d = pd.read_csv(FILES[tf])
        d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
        d = d.rename(columns={'tick_volume': 'vol'})[['open', 'high', 'low', 'close', 'spread', 'vol']].astype(float)
    _cache[tf] = d
    return d


def htf(d, tf, values):
    """Map a higher-timeframe series (indexed by bar open) onto d's bars using only CLOSED htf bars."""
    x = load(tf) if isinstance(tf, str) else tf
    mins = {'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240, 'D1': 1440}[tf] if isinstance(tf, str) else None
    s = pd.Series(np.asarray(values, float), index=x.index + pd.Timedelta(minutes=mins))
    return s.reindex(d.index.union(s.index)).ffill().reindex(d.index).values


# ---------- indicators (MT5 definitions) ----------
def ema(x, n): return x.ewm(span=n, adjust=False).mean()
def sma(x, n): return x.rolling(n).mean()
def rma(x, n): return x.ewm(alpha=1 / n, adjust=False).mean()


def atr(d, n=14, kind='sma'):
    pc = d.close.shift()
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean() if kind == 'sma' else rma(tr, n)   # MT5 iATR = SMA of TR


def rsi(c, n=14):
    dd = c.diff()
    return 100 - 100 / (1 + rma(dd.clip(lower=0), n) / rma((-dd).clip(lower=0), n))


def adx(d, n=14):
    """MT5 iADX style (EMA smoothing of +DM/-DM/TR)."""
    up = d.high.diff(); dn = -d.low.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = d.close.shift()
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    a = 2 / (n + 1)
    trs = tr.ewm(alpha=a, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=d.index).ewm(alpha=a, adjust=False).mean() / trs
    mdi = 100 * pd.Series(mdm, index=d.index).ewm(alpha=a, adjust=False).mean() / trs
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return dx.ewm(alpha=a, adjust=False).mean(), pdi, mdi


def stoch(d, k=5, dp=3, slow=3):
    lo = d.low.rolling(k).min(); hi = d.high.rolling(k).max()
    kk = 100 * (d.close - lo).rolling(slow).sum() / (hi - lo).rolling(slow).sum()
    return kk, kk.rolling(dp).mean()


def macd(c, f=12, s=26, sig=9):
    m = ema(c, f) - ema(c, s)
    return m, m.rolling(sig).mean()   # MT5 iMACD signal line is an SMA


def tod(d): return (d.index.hour * 60 + d.index.minute).values.astype(np.int64)


# ---------- simulator ----------
@njit(cache=True)
def _run(o, h, l, c, tmin, dow, dayid, sig, sl_d, tp_d, ent_px, xl, xs,
         be_trig_a, be_off_a, tr_start_a, tr_dist_a, tr_step, max_bars, eod, fri_eod,
         max_day, dll, cool, opp_exit, spread, slip, tpt_l, tpt_s, tp_floor, tp_expand, slt_l, slt_s):
    n = len(o)
    out = np.zeros((n, 8))   # entry_i, exit_i, dir, entry, exit, gross, swap, reason
    k = 0
    pos = 0; ei = 0; ent = 0.0; sl = 0.0; tp = 0.0; best = 0.0
    be_trig = 0.0; be_off = 0.0; tr_start = 0.0; tr_dist = 0.0
    cur = -1; nday = 0; dpnl = 0.0; cool_until = -1
    for i in range(1, n):
        if dayid[i] != cur:
            cur = dayid[i]; nday = 0; dpnl = 0.0
        intrabar_exit = False
        # ---- manage open position on bar i ----
        if pos != 0:
            px = 0.0; why = 0
            ask_o = o[i] + spread; ask_h = h[i] + spread; ask_l = l[i] + spread
            # bar-close driven target / stop updates (decided on bar i-1, live from bar i)
            if pos == 1:
                if tpt_l[i - 1] > 0:
                    nt = tpt_l[i - 1]
                    if tp_floor > 0 and nt < ent + tp_floor: nt = ent + tp_floor
                    if nt > o[i] and (tp_expand == 0 or nt > tp): tp = nt
                if slt_l[i - 1] > 0 and slt_l[i - 1] > sl and slt_l[i - 1] < o[i]: sl = slt_l[i - 1]
            else:
                if tpt_s[i - 1] > 0:
                    nt = tpt_s[i - 1]
                    if tp_floor > 0 and nt > ent - tp_floor: nt = ent - tp_floor
                    if nt < ask_o and (tp_expand == 0 or nt < tp): tp = nt
                if slt_s[i - 1] > 0 and (slt_s[i - 1] < sl or sl == 0.0) and slt_s[i - 1] > ask_o: sl = slt_s[i - 1]
            # exits decided on the previous closed bar fill at this open
            if i - 1 >= ei:
                if (pos == 1 and xl[i - 1]) or (pos == -1 and xs[i - 1]) or \
                   (opp_exit and sig[i - 1] == -pos):
                    px = o[i] - slip if pos == 1 else ask_o + slip; why = 4
            if why == 0 and max_bars > 0 and i - ei >= max_bars:
                px = o[i] - slip if pos == 1 else ask_o + slip; why = 5
            if why == 0 and ((eod >= 0 and tmin[i] >= eod) or (fri_eod >= 0 and dow[i] == 4 and tmin[i] >= fri_eod)
                             or (dayid[i] != dayid[i - 1] and eod >= 0)):
                px = o[i] - slip if pos == 1 else ask_o + slip; why = 6
            if why == 0:
                if pos == 1:
                    if sl > 0 and o[i] <= sl: px = o[i] - slip; why = 1
                    elif sl > 0 and l[i] <= sl: px = sl - slip; why = 1
                    elif tp > 0 and o[i] >= tp: px = o[i]; why = 2
                    elif tp > 0 and h[i] >= tp: px = tp; why = 2
                else:
                    if sl > 0 and ask_o >= sl: px = ask_o + slip; why = 1
                    elif sl > 0 and ask_h >= sl: px = sl + slip; why = 1
                    elif tp > 0 and ask_o <= tp: px = ask_o; why = 2
                    elif tp > 0 and ask_l <= tp: px = tp; why = 2
            if why != 0:
                g = (px - ent) if pos == 1 else (ent - px)
                # swap: nights crossed
                nights = 0.0
                for j in range(ei + 1, i + 1):
                    if dayid[j] != dayid[j - 1]:
                        nights += 3.0 if dow[j - 1] == 2 else 1.0
                sw = nights * (SWAP_L if pos == 1 else SWAP_S)
                out[k, 0] = ei; out[k, 1] = i; out[k, 2] = pos; out[k, 3] = ent; out[k, 4] = px
                out[k, 5] = g; out[k, 6] = sw; out[k, 7] = why; k += 1
                dpnl += g - sw
                if g - sw < 0 and cool > 0: cool_until = i + cool
                pos = 0
                intrabar_exit = why == 1 or why == 2   # a stop/target inside bar i: no re-entry at bar i's (earlier) open
            else:
                # trailing / breakeven from this bar's extreme (active next bar)
                if pos == 1:
                    if h[i] > best: best = h[i]
                    fav = best - ent
                    if be_trig > 0 and fav >= be_trig and sl < ent + be_off: sl = ent + be_off
                    if tr_dist > 0 and fav >= tr_start:
                        ns = best - tr_dist
                        if ns >= sl + tr_step or sl == 0.0: sl = max(sl, ns)
                else:
                    if l[i] + spread < best or best == 0.0: best = l[i] + spread
                    fav = ent - best
                    if be_trig > 0 and fav >= be_trig and (sl > ent - be_off or sl == 0.0): sl = ent - be_off
                    if tr_dist > 0 and fav >= tr_start:
                        ns = best + tr_dist
                        if sl == 0.0 or ns <= sl - tr_step: sl = ns if sl == 0.0 else min(sl, ns)
        # ---- new entry from signal on closed bar i-1 ----
        if pos == 0 and not intrabar_exit and sig[i - 1] != 0 and i > cool_until:
            if (max_day > 0 and nday >= max_day) or (dll > 0 and dpnl <= -dll):
                continue
            if eod >= 0 and tmin[i] >= eod: continue
            if dayid[i] != dayid[i - 1] and eod >= 0: continue   # signal from yesterday's last bar
            d_ = int(sig[i - 1]); e = 0.0
            if ent_px[i - 1] != 0.0:
                # pending stop/limit order at ent_px placed after bar i-1, valid for bar i only
                lvl = ent_px[i - 1]
                if d_ == 1:
                    if lvl >= o[i] + spread and h[i] + spread >= lvl: e = lvl + slip      # buy stop
                    elif lvl < o[i] + spread and l[i] + spread <= lvl: e = lvl            # buy limit
                else:
                    if lvl <= o[i] and l[i] <= lvl: e = lvl - slip                          # sell stop
                    elif lvl > o[i] and h[i] >= lvl: e = lvl                                # sell limit
                if e == 0.0: continue
            else:
                e = o[i] + spread + slip if d_ == 1 else o[i] - slip
            pos = d_; ei = i; ent = e; nday += 1
            be_trig = be_trig_a[i - 1]; be_off = be_off_a[i - 1]; tr_start = tr_start_a[i - 1]; tr_dist = tr_dist_a[i - 1]
            sl = ent - sl_d[i - 1] * d_ if sl_d[i - 1] > 0 else 0.0
            tp = ent + tp_d[i - 1] * d_ if tp_d[i - 1] > 0 else 0.0
            best = ent
            # same-bar exit check for the entry bar (stop first)
            if d_ == 1:
                if sl > 0 and l[i] <= sl:
                    px = sl - slip; why = 1
                elif tp > 0 and h[i] >= tp and ent_px[i - 1] == 0.0:
                    px = tp; why = 2
                else:
                    why = 0
            else:
                if sl > 0 and h[i] + spread >= sl:
                    px = sl + slip; why = 1
                elif tp > 0 and l[i] + spread <= tp and ent_px[i - 1] == 0.0:
                    px = tp; why = 2
                else:
                    why = 0
            if why != 0:
                g = (px - ent) if d_ == 1 else (ent - px)
                out[k, 0] = ei; out[k, 1] = i; out[k, 2] = d_; out[k, 3] = ent; out[k, 4] = px
                out[k, 5] = g; out[k, 6] = 0.0; out[k, 7] = why; k += 1
                dpnl += g
                if g < 0 and cool > 0: cool_until = i + cool
                pos = 0
    return out[:k]


REASONS = {1: 'stop', 2: 'target', 4: 'signal', 5: 'time', 6: 'session_end'}


def simulate(d, sig, sl=0, tp=0, ent_px=None, exit_long=None, exit_short=None,
             be_trig=0.0, be_off=0.0, trail_start=0.0, trail_dist=0.0, trail_step=0.0,
             max_bars=0, eod=None, fri_eod=None, max_day=0, daily_loss=0.0, cooldown=0,
             opp_exit=False, spread=SPREAD, slip=SLIP, tp_track_long=None, tp_track_short=None, tp_floor=0.0,
             tp_expand=False, sl_track_long=None, sl_track_short=None):
    """sig/sl/tp arrays aligned to d (decided on that bar's close). sl/tp are $ distances (0 = none).
    eod/fri_eod: server minute-of-day after which open trades are closed and no new trades start.
    be_trig/be_off/trail_start/trail_dist may be arrays (value taken from the signal bar).
    tp_track_*: target re-set each bar to this level (if still beyond price; tp_floor = min distance from entry,
    tp_expand = only move it further away). sl_track_*: stop raised (long) / lowered (short) to this level.
    max_bars: close at the open of the bar max_bars after the entry bar."""
    n = len(d)
    arr = lambda x, dt=float: np.broadcast_to(np.nan_to_num(np.asarray(x, dt)), (n,)).astype(dt).copy()
    days = d.index.normalize()
    _, dayid = np.unique(days.values, return_inverse=True)
    out = _run(d.open.values, d.high.values, d.low.values, d.close.values, tod(d), d.index.dayofweek.values.astype(np.int64),
               dayid.astype(np.int64), arr(sig), arr(sl), arr(tp), arr(0 if ent_px is None else ent_px),
               arr(False if exit_long is None else exit_long, np.bool_), arr(False if exit_short is None else exit_short, np.bool_),
               arr(be_trig), arr(be_off), arr(trail_start), arr(trail_dist), float(trail_step), int(max_bars),
               -1 if eod is None else int(eod), -1 if fri_eod is None else int(fri_eod),
               int(max_day), float(daily_loss), int(cooldown), bool(opp_exit), float(spread), float(slip),
               arr(0 if tp_track_long is None else tp_track_long), arr(0 if tp_track_short is None else tp_track_short),
               float(tp_floor), int(tp_expand), arr(0 if sl_track_long is None else sl_track_long),
               arr(0 if sl_track_short is None else sl_track_short))
    t = pd.DataFrame(out, columns=['ei', 'xi', 'dir', 'entry', 'exit', 'gross', 'swap', 'why'])
    t['entry_time'] = d.index[t.ei.astype(int)]; t['exit_time'] = d.index[t.xi.astype(int)]
    t['pnl'] = t.gross - t.swap
    t['why'] = t.why.astype(int).map(REASONS)
    return t


def daily(t, d):
    days = pd.DatetimeIndex(np.unique(d.index.normalize()))
    p = t.groupby(t.exit_time.dt.normalize()).pnl.sum() if len(t) else pd.Series(dtype=float)
    return p.reindex(days, fill_value=0.0)


def stats(t, d, label=''):
    p = daily(t, d); eq = p.cumsum(); m = p.groupby(p.index.to_period('M')).sum()
    w = t.pnl[t.pnl > 0].sum(); ls = -t.pnl[t.pnl < 0].sum()
    return dict(bot=label, trades=len(t), per_day=round(p.mean(), 2), win=round((t.pnl > 0).mean() * 100, 1) if len(t) else np.nan,
                pf=round(w / ls, 2) if ls > 0 else np.nan, avg=round(t.pnl.mean(), 2) if len(t) else np.nan,
                trades_day=round(len(t) / len(p), 2), max_dd=round((eq - eq.cummax()).min(), 0),
                worst_trade=round(t.pnl.min(), 0) if len(t) else np.nan, worst_month=round(m.min(), 0),
                pos_months=f'{(m > 0).sum()}/{len(m)}', total=round(p.sum(), 0), days=len(p))


def by_year(t, d):
    p = daily(t, d)
    return p.groupby(p.index.year).mean().round(2).to_dict()


def coinflip(d, sig, runs=100, seed=1, **kw):
    """Same entry bars and exit rules, random direction. Returns $/day for each run."""
    rng = np.random.default_rng(seed); s = np.asarray(sig, float); nz = s != 0; res = []
    for _ in range(runs):
        r = s.copy(); r[nz] = np.where(rng.random(nz.sum()) < .5, 1.0, -1.0)
        kw2 = dict(kw)
        if kw2.get('ent_px') is not None:
            kw2.pop('ent_px')   # market entries for random runs
        res.append(daily(simulate(d, r, **kw2), d).mean())
    return np.array(res)
