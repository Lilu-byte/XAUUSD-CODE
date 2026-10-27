"""exits-stacking family helpers.
- TrainH(): mlib Harness on TRAIN rows only (TEST is never simulated during exploration).
- run_pw(): copy of mlib._sim that also returns each trade's win PROBABILITY (FAIR mixed bars give
  q = random-walk chance TP came first, so counting pnl>0 is wrong there) and supports fill='RAND'
  (draw TP/SL with prob q, i.e. one realised path) for honest worst-day numbers.
- summ(): mlib.summarize + expected win rate + per-half-of-train per_day (stability check).
"""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *
import numpy as np, pandas as pd
from numba import njit

OUT = '/mnt/project-files/xauusd-microscalp/families/exits-stacking/'
FILLX = dict(FILL, RAND=4)


SPREAD_START = pd.Timestamp('2026-07-08 11:00')   # MT5 recorded ~0 spread before this (not real)


def repaired_m1(m=None):
    """M1 with the unrecorded (~0) spreads before SPREAD_START replaced by the hour-of-day median spread of
    TRAIN bars from SPREAD_START to SPLIT. TEST rows are untouched."""
    m = load_m1() if m is None else m.copy()
    ref = m[(m.index >= SPREAD_START) & (m.index < SPLIT)]
    med = ref.groupby(ref.index.hour).spread.median()
    early = m.index < SPREAD_START
    m.loc[early, 'spread'] = med.reindex(m.index[early].hour).values
    m['spread_usd'] = m.spread * 0.01
    return m


def TrainH(repair=True):
    m = repaired_m1() if repair else load_m1()
    return Harness(m[m.index < SPLIT])


def full_m1():
    return load_m1()


@njit(cache=True)
def _simpw(o, h, l, c, spr, tod, day, sig, tp, sl, timeout, max_open, fill, day_target, day_loss, cooldown, seed):
    np.random.seed(seed)
    n = len(c)
    nd = day[-1] + 1
    dpnl = np.zeros(nd); dtr = np.zeros(nd)
    t_in = np.empty(n, np.int64); t_out = np.empty(n, np.int64); t_pnl = np.empty(n); t_dir = np.empty(n, np.int64)
    t_pw = np.empty(n); t_kind = np.empty(n, np.int64)   # kind 0=TP 1=SL 2=mixed bar 3=timeout/gap/eod
    nt = 0
    pdir = np.zeros(max_open, np.int64); pent = np.zeros(max_open); pidx = np.full(max_open, -1, np.int64)
    pact = np.zeros(max_open, np.bool_); pslot = np.zeros(max_open, np.int64)
    cur = -1; dsum = 0.0; halted = False; last_entry = -1000000
    for i in range(n):
        if day[i] != cur:
            cur = day[i]; dsum = 0.0; halted = False
        for k in range(max_open):
            if not pact[k] or pidx[k] >= i: continue
            e = pent[k]; s = pdir[k]; ex = False; px = 0.0; pw = -1.0; kind = 3
            a = spr[i]
            stale = (i - pidx[k] >= timeout) or (tod[i] >= END_TOD) or (i == n - 1) or (day[i] != day[pidx[k]])
            if s == 1:
                tpp = e + tp; slp = e - sl
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
            else:
                tpp = e - tp; slp = e + sl
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
        if s != 0 and not halted and tod[i] < END_TOD - 15 and i < n - 1 and i - last_entry >= cooldown:
            for k in range(max_open):
                if not pact[k]:
                    pact[k] = True; pdir[k] = s; pidx[k] = i; pslot[k] = nt
                    pent[k] = c[i] + spr[i] if s == 1 else c[i]
                    t_in[nt] = i; t_dir[nt] = s; t_out[nt] = -1; t_pnl[nt] = 0.0; t_pw[nt] = 0.0; t_kind[nt] = 3
                    nt += 1; dtr[day[i]] += 1; last_entry = i
                    break
    return dpnl, dtr, t_in[:nt], t_out[:nt], t_pnl[:nt], t_dir[:nt], t_pw[:nt], t_kind[:nt]


def run_pw(H, sig, tp, sl, timeout=10, max_open=1, fill='FAIR', spread='base', day_target=0.0, day_loss=0.0,
           cooldown=0, seed=0):
    sig = np.nan_to_num(np.asarray(sig, float)).astype(np.int64)
    dp, dt, ti, to, tpn, tdr, tpw, tk = _simpw(H.o, H.h, H.l, H.c, H._spr[spread], H.tod, H.day, sig, float(tp),
                                               float(sl), int(timeout), int(max_open), FILLX[fill],
                                               float(day_target), float(day_loss), int(cooldown), int(seed))
    days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=H.dates)
    trades = pd.DataFrame({'entry': H.m1.index[ti], 'dir': tdr, 'pnl': tpn, 'pwin': tpw, 'kind': tk,
                           'bars': np.where(to >= 0, to - ti, -1), 'spr': H._spr[spread][ti]})
    return days, trades


HALF = pd.Timestamp('2026-08-01')


def summ(days, trades, period=None):
    r = summarize(days, trades, period)
    r['pwin'] = trades.pwin.mean() if 'pwin' in trades and len(trades) else np.nan
    if period in (None, 'train'):
        d = days[days.index < SPLIT]
        r['pd_jul'] = d[d.index < HALF].pnl.mean(); r['pd_aug'] = d[d.index >= HALF].pnl.mean()
    return r


def gate(sig, m1, g, lag=0):
    """Keep signals only where the recorded spread (of bar i, or bar i-lag) is <= g dollars."""
    s = m1.spread_usd.shift(lag).values if lag else m1.spread_usd.values
    return np.where(s <= g + 1e-9, sig, 0)
