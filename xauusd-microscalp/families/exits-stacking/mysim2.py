"""exits-stacking family helpers, mlib v2 conventions (rewritten 2026-10-14; the v1-based originals are in v1_old/).

run_pw(H, sig, ...): a copy of mlib v2 _sim (same entry window 01:05-22:29, force-close at 22:58 / last bar of the
session, same fills) that additionally returns per trade
  pwin  = win PROBABILITY (FAIR mixed bars: q = random-walk chance the TP came first; elsewhere 1/0)
  kind  = 0 TP, 1 SL, 2 both inside one bar (mixed), 3 timeout / session end / gap
  spr   = spread model value at entry
and supports
  fill='RAND'  one realised path per seed: in a mixed bar the TP is taken with probability q (same expectation as
               FAIR, but a real win/loss sequence, needed for day_target / day_loss and worst-day numbers)
  be_trig/be_lock  break-even stop: if at a bar CLOSE the position shows >= be_trig profit (bid for longs, ask for
               shorts), the stop is moved to entry +/- be_lock from the next bar on (0 = off).
check_equal() verifies that run_pw == mlib.Harness.run for FAIR/OHLC fills.
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *
from mlib import END_TOD, LAST_ENTRY_TOD, FIRST_ENTRY_TOD
import numpy as np, pandas as pd
from numba import njit

OUT = '/mnt/project-files/xauusd-microscalp/families/exits-stacking/'
FILLX = dict(FILL, RAND=4)
HALF = pd.Timestamp('2026-08-01')     # inner TRAIN split: A = Jun 26 - Jul 31 (flat month), B = Aug (strong up-trend)


@njit(cache=True)
def _simpw(o, h, l, c, spr, tod, day, last, sig, tp, sl, timeout, max_open, fill, day_target, day_loss, cooldown,
           be_trig, be_lock, seed):
    np.random.seed(seed)
    n = len(c)
    nd = day[-1] + 1
    dpnl = np.zeros(nd); dtr = np.zeros(nd)
    t_in = np.empty(n, np.int64); t_out = np.empty(n, np.int64); t_pnl = np.empty(n); t_dir = np.empty(n, np.int64)
    t_pw = np.empty(n); t_kind = np.empty(n, np.int64)
    nt = 0
    pdir = np.zeros(max_open, np.int64); pent = np.zeros(max_open); pidx = np.full(max_open, -1, np.int64)
    pact = np.zeros(max_open, np.bool_); pslot = np.zeros(max_open, np.int64); psl = np.zeros(max_open)
    cur = -1; dsum = 0.0; halted = False; last_entry = -1000000
    for i in range(n):
        if day[i] != cur:
            cur = day[i]; dsum = 0.0; halted = False
        for k in range(max_open):
            if not pact[k] or pidx[k] >= i: continue
            e = pent[k]; s = pdir[k]; ex = False; px = 0.0; pw = -1.0; kind = 3
            a = spr[i]
            stale = (i - pidx[k] >= timeout) or (tod[i] >= END_TOD) or last[i] or (i == n - 1) or (day[i] != day[pidx[k]])
            if s == 1:
                tpp = e + tp; slp = psl[k]
                if day[i] != day[pidx[k]]: px = o[i]; ex = True
                elif o[i] <= slp or o[i] >= tpp: px = o[i]; ex = True
                else:
                    hit_t = h[i] >= tpp; hit_s = l[i] <= slp
                    if hit_t and hit_s:
                        q = (o[i] - slp) / (tpp - slp)
                        if fill == 0: px = slp; pw = 0.0
                        elif fill == 3: px = tpp; pw = 1.0
                        elif fill == 2:
                            px = slp if c[i] > o[i] else tpp
                            pw = 1.0 if px == tpp else 0.0
                        elif fill == 4:
                            px = tpp if np.random.random() < q else slp
                            pw = 1.0 if px == tpp else 0.0
                        else:
                            px = q * tpp + (1 - q) * slp; pw = q
                        ex = True; kind = 2
                    elif hit_t: px = tpp; ex = True; kind = 0
                    elif hit_s: px = slp; ex = True; kind = 1
                if not ex and stale: px = c[i]; ex = True
                pnl = px - e
                if not ex and be_trig > 0 and c[i] - e >= be_trig and psl[k] < e + be_lock: psl[k] = e + be_lock
            else:
                tpp = e - tp; slp = psl[k]
                ao = o[i] + a; ah = h[i] + a; al = l[i] + a; ac = c[i] + a
                if day[i] != day[pidx[k]]: px = ao; ex = True
                elif ao >= slp or ao <= tpp: px = ao; ex = True
                else:
                    hit_t = al <= tpp; hit_s = ah >= slp
                    if hit_t and hit_s:
                        q = (slp - ao) / (slp - tpp)
                        if fill == 0: px = slp; pw = 0.0
                        elif fill == 3: px = tpp; pw = 1.0
                        elif fill == 2:
                            px = tpp if c[i] > o[i] else slp
                            pw = 1.0 if px == tpp else 0.0
                        elif fill == 4:
                            px = tpp if np.random.random() < q else slp
                            pw = 1.0 if px == tpp else 0.0
                        else:
                            px = q * tpp + (1 - q) * slp; pw = q
                        ex = True; kind = 2
                    elif hit_t: px = tpp; ex = True; kind = 0
                    elif hit_s: px = slp; ex = True; kind = 1
                if not ex and stale: px = ac; ex = True
                pnl = e - px
                if not ex and be_trig > 0 and e - ac >= be_trig and psl[k] > e - be_lock: psl[k] = e - be_lock
            if ex:
                pact[k] = False
                j = pslot[k]
                t_out[j] = i; t_pnl[j] = pnl
                if pw < 0: pw = 1.0 if pnl > 0 else 0.0
                t_pw[j] = pw; t_kind[j] = kind
                dpnl[day[pidx[k]]] += pnl
                if day[pidx[k]] == cur:
                    dsum += pnl
                    if (day_target > 0 and dsum >= day_target) or (day_loss > 0 and dsum <= -day_loss): halted = True
        s = sig[i]
        if s != 0 and not halted and tod[i] <= LAST_ENTRY_TOD and tod[i] >= FIRST_ENTRY_TOD and not last[i] and i < n - 1 and i - last_entry >= cooldown:
            for k in range(max_open):
                if not pact[k]:
                    pact[k] = True; pdir[k] = s; pidx[k] = i; pslot[k] = nt
                    pent[k] = c[i] + spr[i] if s == 1 else c[i]
                    psl[k] = pent[k] - sl if s == 1 else pent[k] + sl
                    t_in[nt] = i; t_dir[nt] = s; t_out[nt] = -1; t_pnl[nt] = 0.0; t_pw[nt] = 0.0; t_kind[nt] = 3
                    nt += 1; dtr[day[i]] += 1; last_entry = i
                    break
    return dpnl, dtr, t_in[:nt], t_out[:nt], t_pnl[:nt], t_dir[:nt], t_pw[:nt], t_kind[:nt]


def run_pw(H, sig, tp, sl, timeout=10, max_open=1, fill='FAIR', spread='base', day_target=0.0, day_loss=0.0,
           cooldown=0, be_trig=0.0, be_lock=0.0, seed=0):
    sig = np.sign(np.nan_to_num(np.asarray(sig, float))).astype(np.int64)
    dp, dt, ti, to, tpn, tdr, tpw, tk = _simpw(H.o, H.h, H.l, H.c, H._spr[spread], H.tod, H.day, H.last, sig,
                                               float(tp), float(sl), int(timeout), int(max_open), FILLX[fill],
                                               float(day_target), float(day_loss), int(cooldown),
                                               float(be_trig), float(be_lock), int(seed))
    days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=H.dates)
    trades = pd.DataFrame({'entry': H.m1.index[ti], 'dir': tdr, 'pnl': tpn, 'pwin': tpw, 'kind': tk,
                           'bars': np.where(to >= 0, to - ti, -1), 'spr': H._spr[spread][ti]})
    return days, trades


def summ(days, trades, period=None):
    """mlib.summarize + probability-weighted win rate + inner-split per_day (TRAIN only)."""
    r = summarize(days, trades, period)
    r['pwin'] = trades.pwin.mean() if 'pwin' in trades and len(trades) else np.nan
    if period in (None, 'train'):
        d = days[days.index < SPLIT]
        r['pd_jul'] = d[d.index < HALF].pnl.mean(); r['pd_aug'] = d[d.index >= HALF].pnl.mean()
    return r


def gate(sig, m1, g, lag=0):
    """Keep signals only where the recorded spread of bar i (or bar i-lag) is <= g dollars (known at bar i close)."""
    s = m1.spread_usd.shift(lag).values if lag else m1.spread_usd.values
    return np.where(s <= g + 1e-9, sig, 0)


def train_harness():
    m1 = load_m1()
    return m1, Harness(m1[m1.index < SPLIT])


def check_equal(H, sig, n=6):
    """run_pw must reproduce mlib v2 Harness.run exactly (FAIR and OHLC, max_open, cooldown, day stops)."""
    cfgs = [(0.3, 0.3, 5, 1, 'FAIR', 0, 0, 0), (0.1, 5.0, 30, 3, 'FAIR', 0, 0, 2), (1.0, 0.5, 10, 10, 'OHLC', 0, 0, 0),
            (0.5, 20.0, 30, 50, 'FAIR', 5, 20, 0), (0.2, 1.0, 3, 5, 'STOP', 0, 0, 1), (0.75, 2.0, 1, 1, 'TARGET', 0, 0, 0)]
    bad = 0
    for tp, sl, to, mo, f, dt, dl, cd in cfgs[:n]:
        d1, t1 = H.run(sig, tp, sl, timeout=to, max_open=mo, fill=f, day_target=dt, day_loss=dl, cooldown=cd)
        d2, t2 = run_pw(H, sig, tp, sl, timeout=to, max_open=mo, fill=f, day_target=dt, day_loss=dl, cooldown=cd)
        ok = np.allclose(d1.pnl.values, d2.pnl.values) and len(t1) == len(t2) and np.allclose(t1.pnl.values, t2.pnl.values)
        bad += not ok
    return bad
