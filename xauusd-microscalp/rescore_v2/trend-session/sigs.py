"""Signal construction: direction filter x entry trigger x session x spread filter.
All inputs come from features.get() (known at the M1 bar's close)."""
from features import *

F = get()
SPR_MED = float(F.spr[F.index < SPLIT].median())   # train median of recorded spread (0.14)


def direction(name):
    f = F
    t4 = f.tr_M5 + f.tr_M15 + f.tr_H1 + f.tr_H4
    if name == 'T4': d = np.where(t4 == 4, 1, np.where(t4 == -4, -1, 0))
    elif name == 'T4L': d = np.where(t4 == 4, 1, 0)
    elif name == 'T4S': d = np.where(t4 == -4, -1, 0)
    elif name == 'T5':
        t5 = t4 + f.tr_M30; d = np.where(t5 == 5, 1, np.where(t5 == -5, -1, 0))
    elif name == 'T5L':
        t5 = t4 + f.tr_M30; d = np.where(t5 == 5, 1, 0)
    elif name == 'T3':  # M15, H1, H4
        t = f.tr_M15 + f.tr_H1 + f.tr_H4; d = np.where(t == 3, 1, np.where(t == -3, -1, 0))
    elif name == 'TH':  # H1 and H4
        t = f.tr_H1 + f.tr_H4; d = np.where(t == 2, 1, np.where(t == -2, -1, 0))
    elif name == 'T4D1':  # T4 and D1 close on the same side of EMA50
        d = np.where((t4 == 4) & (f.d1_side > 0), 1, np.where((t4 == -4) & (f.d1_side < 0), -1, 0))
    elif name.startswith('NY'):  # NY5, NY7, NY5x (no D1 filter)
        thr = int(name[2]); nod1 = name.endswith('x')
        up = (f.ny_buy >= thr) & (nod1 | (f.d1 > 0))
        dn = (f.ny_sell >= thr) & (nod1 | (f.d1 < 0))
        d = np.where(up & ~dn, 1, np.where(dn & ~up, -1, 0))
    elif name == 'T4NY':
        d = np.where((t4 == 4) & (f.ny_buy >= 5), 1, np.where((t4 == -4) & (f.ny_sell >= 5), -1, 0))
    else: raise ValueError(name)
    return pd.Series(d, index=f.index).fillna(0).astype(int).values


def trigger(name, d):
    """Boolean mask: trigger condition for a trade in direction d (+1/-1) at this bar."""
    f = F; m = load_m1() if not hasattr(trigger, 'm') else trigger.m
    trigger.m = m
    c, o, h, l = m.close.values, m.open.values, m.high.values, m.low.values
    L = d > 0; S = d < 0
    nred, ngrn = f.nred.values, f.ngrn.values
    ncnt = np.where(L, nred, np.where(S, ngrn, 0))          # counter-trend run length
    nwith = np.where(L, ngrn, np.where(S, nred, 0))         # with-trend run length
    prev_cnt = np.r_[0, np.where(L[1:], nred[:-1], ngrn[:-1])]
    if name == 'all': return np.ones(len(d), bool)
    if name in ('pb1', 'pb2', 'pb3'): return ncnt == int(name[2])
    if name == 'pbge2': return ncnt >= 2
    if name == 'rev2': return (nwith == 1) & (prev_cnt >= 2)       # first with-trend bar after >=2 counter bars
    if name == 'rev1': return (nwith == 1) & (prev_cnt >= 1)
    if name.startswith('rsi'):                                     # rsi7_30 -> RSI7<30 long / >70 short
        n, t = name[3:].split('_'); r = f['rsi' + n].values; t = float(t)
        return np.where(L, r < t, np.where(S, r > 100 - t, False))
    if name == 'touch1':  # low pierces M1 EMA20 and close back on trend side
        e = f.ema20_M1.values
        return np.where(L, (l <= e) & (c > e), np.where(S, (h >= e) & (c < e), False))
    if name == 'touch5':
        e = f.ema20_M5.values
        return np.where(L, (l <= e) & (c > e), np.where(S, (h >= e) & (c < e), False))
    if name == 'below1':  # close on the wrong side of M1 EMA20 (pullback)
        e = f.ema20_M1.values
        return np.where(L, c < e, np.where(S, c > e, False))
    if name.startswith('bo'):  # bo10: close beyond prior 10-bar extreme in trend direction
        n = int(name[2:])
        return np.where(L, c > f[f'hh{n}'].values, np.where(S, c < f[f'll{n}'].values, False))
    if name.startswith('fade'):  # fade10: close beyond prior n-bar extreme AGAINST trend (deep pullback)
        n = int(name[4:])
        return np.where(L, c < f[f'll{n}'].values, np.where(S, c > f[f'hh{n}'].values, False))
    if name == 'f5pb':  # forming M5 candle is counter-trend so far (after >=2 minutes)
        fo = f.f5_open.values; fm = f.f5_min.values
        return (fm >= 2) & np.where(L, c < fo, np.where(S, c > fo, False))
    if name == 'f5go':  # forming M5 candle with trend so far, M1 bar with trend
        fo = f.f5_open.values; fm = f.f5_min.values
        return (fm >= 2) & np.where(L, (c > fo) & (c > o), np.where(S, (c < fo) & (c < o), False))
    if name == 'mom1': return nwith >= 1
    if name == 'mom3': return np.where(L, f.ret3.values > 0, np.where(S, f.ret3.values < 0, False)) & (nwith >= 1)
    raise ValueError(name)


def session(name):
    t = F.tod.values
    if name == 'all': return t >= 0
    if name == 'ex1_3': return (t >= 180) & (t < 22 * 60 + 40)
    if name == 'lon': return (t >= 600) & (t < 780)          # 10:00-12:59
    if name == 'ny': return (t >= 930) & (t < 1080)          # 15:30-17:59
    if name == 'lonny': return ((t >= 600) & (t < 780)) | ((t >= 930) & (t < 1080))
    if name == 'day': return (t >= 540) & (t < 1320)         # 09:00-21:59
    if name == 'asia': return (t >= 180) & (t < 540)
    raise ValueError(name)


def spreadf(name):
    if name == 'any': return np.ones(len(F), bool)
    if name == 'lo': return F.spr.values < SPR_MED
    raise ValueError(name)


def make(dname, gname, sname='all', pname='any'):
    d = direction(dname)
    mask = trigger(gname, d) & session(sname) & spreadf(pname) & (d != 0)
    return np.where(mask, d, 0)
