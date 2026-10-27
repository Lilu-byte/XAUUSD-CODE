"""GoldAllAgree variants: a cached, extended copy of harness.allagree() (17 Oct 2026).

Family: "more trades from GoldAllAgree's trend rule". Everything here is one 0.01 lot.

Rule pieces (all known at a base-bar close, higher timeframes only from completed bars, as harness):
- sig(base, tf, fast, slow): sign of EMA(fast) - EMA(slow) on timeframe tf, aligned to base closes.
- agree(...): True where at least `need` of `tfs` point `side` way (harness.allagree's `on`).
- armed_reentry(...): GoldAllAgree, plus re-entries on the fastest timeframe alone while the slow
  "anchor" timeframes have stayed the right way since the last time all agreed.
- cooldown(...): after an exit, no new entry for n base bars.
- sibling(...): a second stream from a faster rule that may only ENTER while GoldAllAgree is flat.
- trades(on, ...): trades from a position array, priced like harness.allagree (cost='bar': long
  buys at close + the bar's recorded spread, sells at the close; short sells at close, buys back at
  close + spread) or with the task's flat costs (cost='fixed': spread $0.30 + slippage $0.10 on each
  fill, scaled by price/4000 on M15/H1 so it is the same % as today). Swap from harness.

Windows: on M15/H1 windows P&L, swap and costs are reported in today's dollars (divided by
entry price / 4000), as harness.pair_parts does for GoldAllAgree; on the pair window (M5) fixed $.
"""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/code')
import numpy as np, pandas as pd
import harness as H
from lib import load as _load, ema, align, MIN

REF = H.REF
_raw, _sig, _base = {}, {}, {}

# timeframes each window's base timeline can use (as harness.pair_parts)
WIN_TFS = {'pair': ('M5', 'M15', 'M30', 'H1', 'H4'),
           'm15_train': ('M15', 'M30', 'H1', 'H4'), 'm15_test': ('M15', 'M30', 'H1', 'H4'),
           'm15_all': ('M15', 'M30', 'H1', 'H4'), 'h1_old': ('H1', 'H4')}


def raw(tf):
    if tf not in _raw: _raw[tf] = _load(tf)
    return _raw[tf]


def base_frame(base):
    """The base timeline exactly as harness.trend_matrix builds it."""
    if base not in _base:
        b = raw('M5') if base == 'M5' else H.load(base)
        bc = b.index + pd.Timedelta(minutes=MIN[base])
        _base[base] = (b, bc, b.close.values.astype(float), b.spread.values * 0.01)
    return _base[base]


def sig(base, tf, fast=20, slow=80):
    k = (base, tf, fast, slow)
    if k not in _sig:
        b, bc, _, _ = base_frame(base)
        d = raw(tf)
        _sig[k] = align(d, tf, bc, np.sign(ema(d.close, fast) - ema(d.close, slow)).values).fillna(0).values
    return _sig[k]


def S(base, tfs, emas):
    """Matrix of signs, one row per tf. emas: (fast, slow) for all, or dict tf -> (fast, slow)."""
    return np.vstack([sig(base, tf, *(emas[tf] if isinstance(emas, dict) else emas)) for tf in tfs])


def agree(base, tfs, emas=(20, 80), need=None, side=1):
    M = S(base, tfs, emas)
    k = len(tfs) if need is None else need
    return ((M > 0) if side == 1 else (M < 0)).sum(0) >= k


def armed_reentry(base, tfs, anchors, fast_tfs, emas=(20, 80), side=1):
    """Long (side=1) whenever all `tfs` agree (GoldAllAgree), and also whenever all `fast_tfs`
    agree while 'armed'. Armed starts at a bar where all tfs agree and lasts while every `anchors`
    tf keeps pointing the same way; it ends at the first close where an anchor turns."""
    full = agree(base, tfs, emas, side=side)
    anc = agree(base, anchors, emas, side=side)
    fst = agree(base, fast_tfs, emas, side=side)
    armed = np.zeros(len(full), bool); a = False
    for i in range(len(full)):
        a = full[i] or (a and anc[i])
        armed[i] = a
    return full | (armed & fst)


def cooldown(on, n):
    """Same position, but after an exit no entry for n base bars."""
    on = np.asarray(on, bool); out = np.zeros(len(on), bool); pos = False; last_exit = -10**9
    for i in range(len(on)):
        if pos and not on[i]: pos = False; last_exit = i
        elif not pos and on[i] and i - last_exit > n: pos = True
        out[i] = pos
    return out


def sibling(main_on, sib_rule, mode='hold'):
    """Second stream: enters only at a close where main is flat and sib_rule is on.
    mode 'hold': exits when sib_rule ends. 'handoff': also exits when main turns on.
    mode 'free': ignores main (an independent second stream)."""
    m = np.asarray(main_on, bool); r = np.asarray(sib_rule, bool)
    out = np.zeros(len(r), bool); pos = False
    for i in range(len(r)):
        if pos and (not r[i] or (mode == 'handoff' and m[i])): pos = False
        elif not pos and r[i] and (mode == 'free' or not m[i]): pos = True
        out[i] = pos
    return out


def trades(base, on, side=1, cost='bar', scale=None):
    """Trades from a position array (one 0.01 lot). Entry and exit at the base-bar close where the
    position changes (the EA acts at that close, i.e. the next bar's open), as harness.allagree."""
    b, bc, c, spr = base_frame(base)
    if scale is None: scale = base != 'M5'
    on = np.asarray(on, bool).astype(int)
    chg = np.diff(np.concatenate([[0], on]))
    ent = np.flatnonzero(chg > 0); ext = np.flatnonzero(chg < 0)
    ent = ent[:len(ext)]                     # a trade still open at the end is dropped (as harness)
    sc = c[ent] / REF if scale else np.ones(len(ent))
    if cost == 'bar':
        if side == 1: e_px, x_px = c[ent] + spr[ent], c[ext]
        else: e_px, x_px = c[ent], c[ext] + spr[ext]
    else:
        fs, fl = 0.30 * sc, 0.10 * sc
        if side == 1: e_px, x_px = c[ent] + fs + fl, c[ext] - fl
        else: e_px, x_px = c[ent] - fl, c[ext] + fs + fl
    et, xt = bc[ent], bc[ext]
    if scale: sc = e_px / REF               # report in today's dollars, as harness.pair_parts
    g = (x_px - e_px) * side
    sw = np.array([H.nights_swap(e, x, side) for e, x in zip(et, xt)])
    t = pd.DataFrame(dict(entry_time=et, exit_time=xt, dir=side, entry_px=e_px, exit_px=x_px,
                          gross=g / sc, swap=sw / sc, pnl=(g - sw) / sc, sc=sc))
    return t


def base_tf(window):
    return H.WINDOWS[window][0]


def baseline_aa(window, cost='bar'):
    """GoldAllAgree as harness.pair_parts runs it on this window, with the chosen cost model."""
    b = base_tf(window)
    return trades(b, agree(b, WIN_TFS[window]), cost=cost)


def random_dir(t, base, n=200, cost='fixed', seed0=0, scale=None):
    """Same entry and exit times, coin-flip direction, priced the same way (cost model, swap).
    Returns an array of n trade-list P&L vectors' daily means is left to the caller: here we return
    a list of DataFrames' pnl columns (one per run) for speed."""
    b, bc, c, spr = base_frame(base)
    if scale is None: scale = base != 'M5'
    pos = pd.Series(np.arange(len(bc)), index=bc)
    ei = pos.reindex(t.entry_time).values; xi = pos.reindex(t.exit_time).values
    sc = c[ei] / REF if scale else np.ones(len(ei))
    out = []
    sw_l = np.array([H.nights_swap(e, x, 1) for e, x in zip(t.entry_time, t.exit_time)])
    sw_s = np.array([H.nights_swap(e, x, -1) for e, x in zip(t.entry_time, t.exit_time)])
    if cost == 'bar':
        long_p = (c[xi] - (c[ei] + spr[ei])) - sw_l
        short_p = (c[ei] - (c[xi] + spr[xi])) - sw_s
    else:
        fs, fl = 0.30 * sc, 0.10 * sc
        long_p = ((c[xi] - fl) - (c[ei] + fs + fl)) - sw_l
        short_p = ((c[ei] - fl) - (c[xi] + fs + fl)) - sw_s
    long_p, short_p = long_p / sc, short_p / sc
    for k in range(n):
        g = np.random.default_rng(seed0 + k)
        d = np.where(g.random(len(ei)) < 0.5, 1, -1)
        out.append(np.where(d == 1, long_p, short_p))
    return out, long_p, short_p
