"""Daily-target simulator for one 0.01 lot of XAUUSD ($1 per $1 move).

Each day: from `start` (server time) take trades in the signal's direction with a
take-profit and stop-loss, stop for the day once the day's P&L reaches `target`
or after `max_tr` trades; force-close everything at 23:30 server (no swap).
Fills: long enters at ask (bid close + spread), exits at bid; TP = limit, SL =
stop filled at the level or at the bar open if it gapped through, plus slippage.
If SL and TP fall in the same bar, the SL is assumed (conservative).
All dollar distances are scaled by price/4000 so older years trade the same
percentage moves as today; P&L is reported in today's dollars. Set P['sc'] to ones
for fixed-dollar TP/SL like the EAs (the M5 rows do). The EA itself is copied
line by line in asia_ea.py.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from lib import load, ema, align
from numba import njit

SPREAD, SLIP, REF = 0.30, 0.10, 4000.0
END = 23 * 60 + 30


@njit(cache=True)
def run(o, h, l, c, sc, day, tod, sig, trig, start, tp, sl, target, max_tr, recover, maxloss):
    n = len(c); ndays = day[-1] + 1
    dpnl = np.zeros(ndays); dtr = np.zeros(ndays)
    pos = 0; ent = 0.0; e_sc = 1.0; tpd = 0.0; sld = 0.0; eday = -1
    cur = -1; dp = 0.0; nt = 0; done = False
    for i in range(n):
        if day[i] != cur:
            cur = day[i]; dp = 0.0; nt = 0; done = False
        if pos != 0:
            ex = False; px = 0.0
            if pos == 1:
                slp = ent - sld; tpp = ent + tpd
                if o[i] <= slp: px = o[i] - SLIP * e_sc; ex = True
                elif l[i] <= slp: px = slp - SLIP * e_sc; ex = True
                elif h[i] >= tpp: px = tpp; ex = True
                elif tod[i] >= END: px = c[i] - SLIP * e_sc; ex = True
                pnl = px - ent
            else:
                a = SPREAD * e_sc
                slp = ent + sld; tpp = ent - tpd
                if o[i] + a >= slp: px = o[i] + a + SLIP * e_sc; ex = True
                elif h[i] + a >= slp: px = slp + SLIP * e_sc; ex = True
                elif l[i] + a <= tpp: px = tpp; ex = True
                elif tod[i] >= END: px = c[i] + a + SLIP * e_sc; ex = True
                pnl = ent - px
            if ex:
                pos = 0; dp += pnl / e_sc; dpnl[cur] = dp
                if eday == cur and (dp >= target - 1e-9 or nt >= max_tr or dp <= -maxloss): done = True   # a trade carried in from yesterday does not use up today's trade
                continue
        if pos == 0 and not done and tod[i] >= start and tod[i] < END - 15 and trig[i] and sig[i] != 0 and nt < max_tr:
            e_sc = sc[i]; pos = int(sig[i]); nt += 1; dtr[cur] += 1; eday = cur
            want = tp
            if recover and dp < 0: want = target - dp
            tpd = want * e_sc; sld = sl * e_sc
            ent = c[i] + (SPREAD + SLIP) * e_sc if pos == 1 else c[i] - SLIP * e_sc
    return dpnl, dtr


def prep(tf):
    d = load(tf)
    d = d[d.index.dayofweek < 5]
    out = dict(o=d.open.values, h=d.high.values, l=d.low.values, c=d.close.values,
               sc=(d.close / REF).values)
    dates = d.index.normalize()
    u, inv = np.unique(dates.values, return_inverse=True)
    out['day'] = inv.astype(np.int64); out['dates'] = pd.DatetimeIndex(u)
    out['tod'] = (d.index.hour * 60 + d.index.minute).values.astype(np.int64)
    sigs = {}
    tr = {}
    for t in ('H1', 'H4'):
        x = load(t); v = np.sign(ema(x.close, 20) - ema(x.close, 80)).values
        tr[t] = align(x, t, d.index, v).fillna(0).values
    m30 = load('M30'); tr['M30'] = align(m30, 'M30', d.index, np.sign(ema(m30.close, 20) - ema(m30.close, 80)).values).fillna(0).values
    m15 = load('M15'); tr['M15'] = align(m15, 'M15', d.index, np.sign(ema(m15.close, 20) - ema(m15.close, 80)).values).fillna(0).values
    D = load('D1'); dv = np.sign(D.close - ema(D.close, 20)).values
    tr['D1'] = align(D, 'D1', d.index, dv).fillna(0).values
    sigs['long'] = np.ones(len(d))
    sigs['coinflip'] = np.where(np.random.default_rng(0).random(len(d)) < .5, 1., -1.)
    for t in ('H1', 'H4', 'D1'):
        sigs[t] = tr[t]
    sigs['H4+H1'] = np.where(tr['H4'] == tr['H1'], tr['H4'], 0)
    sigs['D1+H4'] = np.where(tr['D1'] == tr['H4'], tr['D1'], 0)
    allag = np.where((tr['H4'] == tr['H1']) & (tr['H1'] == tr['M30']) & (tr['M30'] == tr['M15']), tr['H4'], 0)
    sigs['all4'] = allag
    # Asian-range breakout: after start, direction of the close outside 00:00-09:00 range
    hi = d.high.where(out['tod'] < 540).groupby(dates).cummax().groupby(dates).ffill()
    lo = d.low.where(out['tod'] < 540).groupby(dates).cummin().groupby(dates).ffill()
    sigs['asia_break'] = np.where(out['tod'] >= 540, np.where(d.close > hi, 1, np.where(d.close < lo, -1, 0)), 0).astype(float)
    for k in list(sigs):
        if k not in ('long', 'coinflip', 'asia_break'):
            sigs[k + ' longonly'] = np.clip(sigs[k], 0, None)
    e = ema(d.close, 20)
    above = (d.close > e).values; below = ~above
    up_x = above & np.r_[False, below[:-1]]; dn_x = below & np.r_[False, above[:-1]]
    out['trig'] = {'any': np.ones(len(d), bool), 'pullback': (up_x, dn_x)}
    out['sigs'] = sigs; out['index'] = d.index
    return out


def sim(P, sig, trig, start, tp, sl, target=5.0, max_tr=1, recover=0, maxloss=1e9):
    s = P['sigs'][sig]
    t = P['trig'][trig]
    if isinstance(t, tuple): t = np.where(s > 0, t[0], np.where(s < 0, t[1], False))
    dp, dt = run(P['o'], P['h'], P['l'], P['c'], P['sc'], P['day'], P['tod'], s.astype(np.float64), t,
                 start, tp, sl, target, max_tr, recover, maxloss)
    return pd.DataFrame({'pnl': dp, 'trades': dt}, index=P['dates'])


def summ(df):
    p = df.pnl; eq = p.cumsum()
    m = p.groupby(p.index.to_period('M')).sum()
    return dict(per_day=p.mean(), hit5=(p >= 4.99).mean(), loss_days=(p < 0).mean(), worst_day=p.min(),
                max_dd=(eq - eq.cummax()).min(), worst_month=m.min(), pos_months=(m > 0).mean(),
                trades_day=df.trades.mean(), total=p.sum(), days=len(p))
