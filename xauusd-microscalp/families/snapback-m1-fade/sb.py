"""snapback-m1-fade: shared code for this family (fade sharp M1 moves, exit on time / small TPs).

Everything here is causal: a value at row i uses bars <= i only.
Trades are simulated the way the EA places them: a signal decided at the close of bar i enters at the OPEN of bar
i+1 (first tick; long at open + spread, short at open), only if bar i+1 follows bar i directly (no gap) and the
recorded spread of bar i+1 is <= $0.50 (ea_replica.run_ea rules). Exit logic is a line-by-line copy of
ea/ea_sim._sim_next (mlib v2), extended with (a) several legs per signal with their own TPs, (b) optional
break-even / trailing stop updated only AFTER a bar has been processed (never inside the bar), and a separate
ladder simulator for the re-entry idea. _simx with one leg and no BE/trail reproduces _sim_next exactly
(checked in check_sim.py).
"""
import sys, numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import load_m1, Harness, SPLIT, FILL, spread_series, random_like, END_TOD, LAST_ENTRY_TOD, FIRST_ENTRY_TOD

FAM = '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade/'
HALF = pd.Timestamp('2026-08-01')          # TRAIN halves: Jun 26-Jul 31 vs Aug
MAX_SPREAD = 0.50                          # EA spread filter at entry (recorded spread of the entry bar)
COMMISSION = 0.07


# ----------------------------------------------------------------------------------------------- features / signals
def feats(m, atr_n=240):
    """Running statistics an MT5 EA can keep: k-bar close change, mean M1 range over atr_n bars (incl. bar i),
    session VWAP since the 01:00 open (typical price x tick volume)."""
    f = pd.DataFrame(index=m.index)
    c = m.close
    for k in (1, 2, 3, 5):
        f[f'r{k}'] = c - c.shift(k)
        f[f'p{k}'] = c.shift(k)                   # pre-spike level
    f['atr'] = (m.high - m.low).rolling(atr_n).mean()
    sess = (m.index - pd.Timedelta(hours=1)).normalize()
    tp = (m.high + m.low + m.close) / 3
    f['vwap'] = (tp * m.tick_volume).groupby(sess).cumsum() / m.tick_volume.groupby(sess).cumsum()
    f['vw_d'] = c - f.vwap
    f['spr_raw'] = m.spread_usd
    return f


def fade_signal(f, k=3, mode='atr', th=3.0, gate='none', fresh=False, sgate=0.0):
    """Direction to TRADE (fade). mode 'atr': |r_k| > th x ATR(240 M1 ranges); mode 'usd': |r_k| > th dollars.
    gate 'away'  : only when the move extends away from the session VWAP (up-move with close > VWAP -> sell; as SF)
         'toward': only when the move runs toward/through VWAP from the other side (up-move with close < VWAP -> sell)
    fresh: only the first bar of a run of signal bars in the same direction.
    sgate: if > 0, only when the signal bar's recorded spread <= sgate dollars."""
    r = f[f'r{k}'].values
    lim = th * f.atr.values if mode == 'atr' else np.full(len(r), th)
    hit = np.abs(r) > lim
    hit &= ~np.isnan(lim)
    d = -np.sign(r)
    if gate == 'away':
        hit &= np.sign(f.vw_d.values) == np.sign(r)
    elif gate == 'toward':
        hit &= np.sign(f.vw_d.values) == -np.sign(r)
    s = np.where(hit, d, 0.0)
    if fresh:
        prev = np.r_[0.0, s[:-1]]
        s = np.where(prev == s, 0.0, s)
    if sgate > 0:
        s = np.where(f.spr_raw.values <= sgate + 1e-9, s, 0.0)
    return np.nan_to_num(s)


def ea_filter(m, s):
    """EA entry rules: next bar follows directly (60 s gap) and its recorded spread <= $0.50."""
    s = np.sign(np.nan_to_num(np.asarray(s, float)))
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10 ** 6]
    raw = m.spread_usd.values
    nxt = np.r_[raw[1:], 99.0]
    return np.where((gap == 60) & (nxt <= MAX_SPREAD + 1e-9), s, 0).astype(np.int64)


def shift1(s):
    """1-bar latency: the signal of bar i is acted on at the close of bar i+1 (enters at the open of i+2)."""
    s = np.asarray(s, float)
    return np.r_[0.0, s[:-1]]


# ----------------------------------------------------------------------------------------------- simulators
@njit(cache=True)
def _simx(o, h, l, c, spr, tod, day, last, sig, tps, sl, timeout, max_open, fill, cooldown, be_trig, be_lock, trail):
    """_sim_next with: len(tps) legs per signal (each its own TP, same SL/timeout; a signal opens all legs only if that
    many slots are free), break-even (be_trig>0: once the best bid (long) / best ask (short) seen on COMPLETED bars is
    be_trig in profit, the stop moves to entry +/- be_lock) and trailing (trail>0: stop follows the best price at
    `trail` distance, completed bars only). One-leg, be_trig=trail=0 is exactly ea_sim._sim_next."""
    n = len(c)
    nd = day[-1] + 1
    nl = len(tps)
    dpnl = np.zeros(nd); dtr = np.zeros(nd)
    cap = n * nl
    t_in = np.empty(cap, np.int64); t_out = np.empty(cap, np.int64); t_pnl = np.empty(cap); t_dir = np.empty(cap, np.int64)
    t_kind = np.empty(cap, np.int64); t_leg = np.empty(cap, np.int64)
    nt = 0
    pdir = np.zeros(max_open, np.int64); pent = np.zeros(max_open); pidx = np.full(max_open, -1, np.int64)
    pact = np.zeros(max_open, np.bool_); pslot = np.zeros(max_open, np.int64); ptp = np.zeros(max_open)
    pslp = np.zeros(max_open); pbest = np.zeros(max_open)
    cur = -1; last_entry = -1000000
    for i in range(n):
        if day[i] != cur:
            cur = day[i]
        for k in range(max_open):
            if not pact[k] or pidx[k] >= i: continue
            e = pent[k]; s = pdir[k]; ex = False; px = 0.0; kind = 3
            a = spr[i]
            stale = (i - pidx[k] >= timeout) or (tod[i] >= END_TOD) or last[i] or (i == n - 1) or (day[i] != day[pidx[k]])
            tp = ptp[k]
            if s == 1:
                tpp = e + tp; slp = pslp[k]
                if day[i] != day[pidx[k]]: px = o[i]; ex = True
                elif o[i] <= slp or o[i] >= tpp:
                    px = o[i]; ex = True; kind = 0 if o[i] >= tpp else 1
                else:
                    hit_t = h[i] >= tpp; hit_s = l[i] <= slp
                    if hit_t and hit_s:
                        if fill == 0: px = slp
                        elif fill == 3: px = tpp
                        elif fill == 2:
                            px = slp if c[i] > o[i] else tpp
                        else:
                            q = (o[i] - slp) / (tpp - slp); px = q * tpp + (1 - q) * slp
                        ex = True; kind = 2
                    elif hit_t: px = tpp; ex = True; kind = 0
                    elif hit_s: px = slp; ex = True; kind = 1
                if not ex and stale: px = c[i]; ex = True; kind = 3
                pnl = px - e
                if not ex:
                    if h[i] > pbest[k]: pbest[k] = h[i]
                    if be_trig > 0 and pbest[k] - e >= be_trig and pslp[k] < e + be_lock: pslp[k] = e + be_lock
                    if trail > 0 and pbest[k] - trail > pslp[k]: pslp[k] = pbest[k] - trail
            else:
                tpp = e - tp; slp = pslp[k]
                ao = o[i] + a; ah = h[i] + a; al = l[i] + a; ac = c[i] + a
                if day[i] != day[pidx[k]]: px = ao; ex = True
                elif ao >= slp or ao <= tpp:
                    px = ao; ex = True; kind = 0 if ao <= tpp else 1
                else:
                    hit_t = al <= tpp; hit_s = ah >= slp
                    if hit_t and hit_s:
                        if fill == 0: px = slp
                        elif fill == 3: px = tpp
                        elif fill == 2:
                            px = tpp if c[i] > o[i] else slp
                        else:
                            q = (slp - ao) / (slp - tpp); px = q * tpp + (1 - q) * slp
                        ex = True; kind = 2
                    elif hit_t: px = tpp; ex = True; kind = 0
                    elif hit_s: px = slp; ex = True; kind = 1
                if not ex and stale: px = ac; ex = True; kind = 3
                pnl = e - px
                if not ex:
                    if al < pbest[k]: pbest[k] = al
                    if be_trig > 0 and e - pbest[k] >= be_trig and pslp[k] > e - be_lock: pslp[k] = e - be_lock
                    if trail > 0 and pbest[k] + trail < pslp[k]: pslp[k] = pbest[k] + trail
            if ex:
                pact[k] = False
                j = pslot[k]
                t_out[j] = i; t_pnl[j] = pnl; t_kind[j] = kind
                dpnl[day[pidx[k]]] += pnl
        s = sig[i]
        if s != 0 and tod[i] <= LAST_ENTRY_TOD and tod[i] >= FIRST_ENTRY_TOD and not last[i] and i < n - 1 and i - last_entry >= cooldown:
            free = 0
            for k in range(max_open):
                if not pact[k]: free += 1
            if free >= nl:
                leg = 0
                for k in range(max_open):
                    if leg >= nl: break
                    if not pact[k]:
                        pact[k] = True; pdir[k] = s; pidx[k] = i; pslot[k] = nt; ptp[k] = tps[leg]
                        pent[k] = o[i + 1] + spr[i + 1] if s == 1 else o[i + 1]
                        pslp[k] = pent[k] - sl if s == 1 else pent[k] + sl
                        pbest[k] = pent[k] - spr[i + 1] if s == 1 else pent[k] + spr[i + 1]
                        t_in[nt] = i; t_dir[nt] = s; t_out[nt] = -1; t_pnl[nt] = 0.0; t_kind[nt] = -1; t_leg[nt] = leg
                        nt += 1; dtr[day[i]] += 1; leg += 1
                last_entry = i
    return dpnl, dtr, t_in[:nt], t_out[:nt], t_pnl[:nt], t_dir[:nt], t_kind[:nt], t_leg[:nt]


@njit(cache=True)
def _simlad(o, h, l, c, spr, raw, tod, day, last, sig, lvl, tp, sl, timeout, lad_max, lad_q, lad_window, mode, fill):
    """Re-entry ladder, one position at a time, every position closes at TP `tp` (<= $1), its stop `sl` or after
    `timeout` bars. A signal at bar i (no ladder active) opens rung 1 at the open of i+1. When a rung's TP fills on
    bar j and the price is still stretched -- the snap-back has recovered less than lad_q of the spike measured from
    the pre-spike level lvl[i] (long: price < lvl - (1-lad_q)*(lvl - close[i])) -- and fewer than lad_max rungs and
    fewer than lad_window bars since the signal, the next rung opens:
      mode 0: stretch checked on bar j's close, entry at the open of bar j+1 (needs j+1 directly after j, spread
              <= $0.50, inside entry hours);
      mode 1: stretch checked at the TP price, re-entry at once at that price (+ spread for a long); the rest of bar
              j is taken as a straight run from the TP price to the close (see the code), so further TPs on that run
              fill inside bar j and a rung can never be credited more than its TP.
    A rung closed by stop or timeout, or a TP fill with the price no longer stretched, ends the ladder."""
    n = len(c)
    nd = day[-1] + 1
    dpnl = np.zeros(nd); dtr = np.zeros(nd)
    cap = 3 * n + 10
    t_in = np.empty(cap, np.int64); t_out = np.empty(cap, np.int64); t_pnl = np.empty(cap); t_dir = np.empty(cap, np.int64)
    t_rung = np.empty(cap, np.int64); t_kind = np.empty(cap, np.int64)
    nt = 0
    act = False; pd_ = 0; pe = 0.0; pi = -1; pslot = 0
    lad = False; ls = 0; l0 = 0.0; lspk = 0.0; li0 = -1; lr = 0
    pend = False
    for i in range(n):
        # pending mode-0 re-entry decided at the close of bar i-1 -> enters at open of bar i
        if pend:
            pend = False
            ok = (i > 0) and (day[i] == day[i - 1]) and (tod[i] - tod[i - 1] == 1) and (raw[i] <= 0.50 + 1e-9) \
                and tod[i - 1] <= LAST_ENTRY_TOD and tod[i - 1] >= FIRST_ENTRY_TOD and not last[i - 1]
            if ok:
                act = True; pd_ = ls; pi = i - 1; pslot = nt
                pe = o[i] + spr[i] if ls == 1 else o[i]
                t_in[nt] = i - 1; t_dir[nt] = ls; t_out[nt] = -1; t_pnl[nt] = 0.0; t_rung[nt] = lr; t_kind[nt] = -1
                nt += 1; dtr[day[i - 1]] += 1
            else:
                lad = False
        if act and pi < i:
            e = pe; s = pd_; ex = False; px = 0.0; kind = 3
            a = spr[i]
            endsess = (tod[i] >= END_TOD) or last[i] or (i == n - 1) or (day[i] != day[pi])
            stale = (i - pi >= timeout) or endsess
            if s == 1:
                tpp = e + tp; slp = e - sl
                if day[i] != day[pi]: px = o[i]; ex = True
                elif o[i] <= slp or o[i] >= tpp:
                    px = o[i]; ex = True; kind = 0 if o[i] >= tpp else 1
                else:
                    hit_t = h[i] >= tpp; hit_s = l[i] <= slp
                    if hit_t and hit_s:
                        if fill == 0: px = slp; kind = 1
                        elif fill == 2:
                            if c[i] > o[i]: px = slp; kind = 1
                            else: px = tpp; kind = 0
                        else:
                            q = (o[i] - slp) / (tpp - slp); px = q * tpp + (1 - q) * slp; kind = 2
                        ex = True
                    elif hit_t: px = tpp; ex = True; kind = 0
                    elif hit_s: px = slp; ex = True; kind = 1
                if not ex and stale: px = c[i]; ex = True; kind = 3
                pnl = px - e
            else:
                tpp = e - tp; slp = e + sl
                ao = o[i] + a; ah = h[i] + a; al = l[i] + a; ac = c[i] + a
                if day[i] != day[pi]: px = ao; ex = True
                elif ao >= slp or ao <= tpp:
                    px = ao; ex = True; kind = 0 if ao <= tpp else 1
                else:
                    hit_t = al <= tpp; hit_s = ah >= slp
                    if hit_t and hit_s:
                        if fill == 0: px = slp; kind = 1
                        elif fill == 2:
                            if c[i] > o[i]: px = tpp; kind = 0
                            else: px = slp; kind = 1
                        else:
                            q = (slp - ao) / (slp - tpp); px = q * tpp + (1 - q) * slp; kind = 2
                        ex = True
                    elif hit_t: px = tpp; ex = True; kind = 0
                    elif hit_s: px = slp; ex = True; kind = 1
                if not ex and stale: px = ac; ex = True; kind = 3
                pnl = e - px
            if ex:
                act = False
                t_out[pslot] = i; t_pnl[pslot] = pnl; t_kind[pslot] = kind
                dpnl[day[pi]] += pnl
                cont = False
                # FAIR mixed fills (kind 2) are a blend of TP and SL: the ladder treats them as ended.
                if kind == 0 and lad and lr < lad_max and (i - li0) < lad_window and not endsess:
                    if mode == 0:
                        ref = c[i] if ls == 1 else c[i] + a      # bid close for a long, ask close for a short
                    else:
                        ref = px
                    lim = l0 - (1 - lad_q) * lspk if ls == 1 else l0 + (1 - lad_q) * lspk
                    if (ls == 1 and ref < lim) or (ls == -1 and ref > lim):
                        cont = True
                if cont:
                    if mode == 0:
                        lr += 1
                        pend = True
                    else:
                        # mode 1: re-enter at once at the TP price. The rest of bar i is assumed to run straight from that
                        # price to the bar's close (no extra excursions): every further TP crossed on that path fills
                        # at its price inside bar i (and the next rung re-enters there); a stop crossed on it fills at
                        # the stop; otherwise the last rung is carried into bar i+1. No credit beyond a TP is possible.
                        lim = l0 - (1 - lad_q) * lspk if ls == 1 else l0 + (1 - lad_q) * lspk
                        while True:
                            if not (tod[i] <= LAST_ENTRY_TOD and not last[i] and i < n - 1 and raw[i] <= 0.50 + 1e-9 and nt < cap - 1):
                                lad = False; break
                            lr += 1
                            ne = px + a if ls == 1 else px - a          # long buys at ask = bid TP price + spread; short sells at bid
                            ntp = ne + tp if ls == 1 else ne - tp
                            nsl = ne - sl if ls == 1 else ne + sl
                            cl = c[i] if ls == 1 else c[i] + a
                            t_in[nt] = i; t_dir[nt] = ls; t_rung[nt] = lr
                            dtr[day[i]] += 1
                            if (ls == 1 and cl >= ntp) or (ls == -1 and cl <= ntp):
                                t_out[nt] = i; t_pnl[nt] = tp; t_kind[nt] = 0; dpnl[day[i]] += tp; nt += 1
                                px = ntp
                                if lr < lad_max and (i - li0) < lad_window and ((ls == 1 and px < lim) or (ls == -1 and px > lim)):
                                    continue
                                lad = False; break
                            elif (ls == 1 and cl <= nsl) or (ls == -1 and cl >= nsl):
                                t_out[nt] = i; t_pnl[nt] = -sl; t_kind[nt] = 1; dpnl[day[i]] -= sl; nt += 1
                                lad = False; break
                            else:
                                act = True; pd_ = ls; pi = i; pslot = nt; pe = ne
                                t_out[nt] = -1; t_pnl[nt] = 0.0; t_kind[nt] = -1; nt += 1
                                break
                else:
                    lad = False
        s = sig[i]
        if s != 0 and not act and not pend and tod[i] <= LAST_ENTRY_TOD and tod[i] >= FIRST_ENTRY_TOD and not last[i] and i < n - 1:
            act = True; pd_ = s; pi = i; pslot = nt
            pe = o[i + 1] + spr[i + 1] if s == 1 else o[i + 1]
            lad = True; ls = s; l0 = lvl[i]; lspk = abs(lvl[i] - c[i]); li0 = i; lr = 1
            t_in[nt] = i; t_dir[nt] = s; t_out[nt] = -1; t_pnl[nt] = 0.0; t_rung[nt] = 1; t_kind[nt] = -1
            nt += 1; dtr[day[i]] += 1
    return dpnl, dtr, t_in[:nt], t_out[:nt], t_pnl[:nt], t_dir[:nt], t_rung[:nt], t_kind[:nt]


# ----------------------------------------------------------------------------------------------- runners
class H2(Harness):
    """mlib Harness + the EA filter and the extended simulators. spread: 'bar' | 'base' | 'wide' | float extra over base."""

    def spr(self, spread):
        if isinstance(spread, str): return self._spr[spread]
        return self._spr['base'] + float(spread)

    def run_x(self, sig, tps=(1000.0,), sl=10.0, timeout=5, max_open=1, cooldown=0, be_trig=0.0, be_lock=0.0, trail=0.0,
              fill='FAIR', spread='base', latency=0, filt=True):
        s = np.asarray(sig, float)
        if latency: s = shift1(s)
        s = ea_filter(self.m1, s) if filt else np.sign(np.nan_to_num(s)).astype(np.int64)
        tps = np.asarray(tps, np.float64)
        dp, dt, ti, to, pn, dr, kd, lg = _simx(self.o, self.h, self.l, self.c, self.spr(spread), self.tod, self.day, self.last,
                                               s, tps, float(sl), int(timeout), int(max_open), FILL[fill], int(cooldown),
                                               float(be_trig), float(be_lock), float(trail))
        days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=self.dates)
        tr = pd.DataFrame({'entry': self.m1.index[ti], 'ei': ti, 'xi': to, 'dir': dr, 'pnl': pn, 'kind': kd, 'leg': lg,
                           'bars': np.where(to >= 0, to - ti, -1)})
        return days, tr

    def run_lad(self, sig, lvl, tp=0.5, sl=10.0, timeout=5, lad_max=5, lad_q=1.0, lad_window=15, mode=0, fill='FAIR',
                spread='base', latency=0, filt=True):
        s = np.asarray(sig, float); lv = np.nan_to_num(np.asarray(lvl, float))
        if latency: s = shift1(s); lv = shift1(lv)
        s = ea_filter(self.m1, s) if filt else np.sign(np.nan_to_num(s)).astype(np.int64)
        dp, dt, ti, to, pn, dr, rg, kd = _simlad(self.o, self.h, self.l, self.c, self.spr(spread), self._spr['bar'], self.tod, self.day, self.last,
                                                 s, lv, float(tp), float(sl), int(timeout), int(lad_max), float(lad_q),
                                                 int(lad_window), int(mode), FILL[fill])
        days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=self.dates)
        tr = pd.DataFrame({'entry': self.m1.index[ti], 'ei': ti, 'xi': to, 'dir': dr, 'pnl': pn, 'rung': rg, 'kind': kd,
                           'bars': np.where(to >= 0, to - ti, -1)})
        return days, tr


def summ(days, tr, period=None, fee=0.0):
    """Per-day statistics. period None/'train'/'test'/'A'/'B' (A, B = TRAIN halves). fee: extra $ per trade (commission)."""
    d = days.copy(); t = tr
    if fee:
        cnt = t.groupby(t.entry.dt.normalize()).size().reindex(d.index, fill_value=0)
        d['pnl'] = d.pnl - fee * cnt.values
        t = t.assign(pnl=t.pnl - fee)
    if period == 'train': sel = d.index < SPLIT
    elif period == 'test': sel = d.index >= SPLIT
    elif period == 'A': sel = d.index < HALF
    elif period == 'B': sel = (d.index >= HALF) & (d.index < SPLIT)
    else: sel = np.ones(len(d), bool)
    d = d[sel]
    t = t[t.entry.dt.normalize().isin(d.index)]
    p = d.pnl; eq = p.cumsum(); nd = max(len(p), 1)
    return dict(per_day=p.mean(), trades_day=len(t) / nd, win=(t.pnl > 0).mean() if len(t) else np.nan,
                per_trade=t.pnl.mean() if len(t) else np.nan, days_ge5=(p >= 4.99).mean(), losing_days=(p < 0).mean(),
                worst_day=p.min(), worst_trade=t.pnl.min() if len(t) else np.nan, max_dd=(eq - eq.cummax()).min(),
                total=p.sum(), days=len(p), long_share=(t.dir == 1).mean() if len(t) else np.nan)


def halves(days, tr):
    a = summ(days, tr, 'A'); b = summ(days, tr, 'B'); t = summ(days, tr, 'train')
    return dict(pd_tr=t['per_day'], pt_tr=t['per_trade'], tpd_tr=t['trades_day'], win_tr=t['win'], wd_tr=t['worst_day'],
                dd_tr=t['max_dd'], pd_A=a['per_day'], pd_B=b['per_day'], ls_tr=t['long_share'], wt_tr=t['worst_trade'])


def load_train():
    m = load_m1()
    m = m[m.index < SPLIT]
    return m, H2(m)


def load_all():
    m = load_m1()
    return m, H2(m)
