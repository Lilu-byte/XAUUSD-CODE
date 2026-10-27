"""Independent reimplementation of the 'Regime-gated Donchian 120/60' candidate, from its written rules only.
Pure-python bar loop, no gbt._run. Written by the verify-reimplement check; does not import candidate code.

Rules (as written):
  regime MOM6 = sign(D1 close / D1 close 126 D1 bars earlier - 1) from last CLOSED D1 bar (server time)
  long if H1 close > max(high of the 120 bars before the signal bar) and MOM6>0 and flat
  short if H1 close < min(low of those 120 bars) and MOM6<0 and flat
  fill at next bar open; stop = 2.5*ATR48(SMA of TR) from the signal bar, measured from the fill
  exit long when H1 close < min(low of previous 60 bars), short when close > max(high prev 60), next open
  spread 0.30 + slip 0.10, stop first, swap 0.126 long / 0.046 short per night, triple Wed
"""
import numpy as np, pandas as pd

SPREAD, SLIP, SWL, SWS = 0.30, 0.10, 0.126, 0.046


def load(path):
    d = pd.read_csv(path)
    d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    return d[['open', 'high', 'low', 'close']].astype(float)


def indicators(h, d1, mom_n=126, ent=120, ex=60, atr_n=48, d1_mode='prevdate'):
    o, hi, lo, c = h.open.values, h.high.values, h.low.values, h.close.values
    n = len(h)
    # rolling extremes of the PREVIOUS k bars (exclude bar itself), plain numpy loops via pandas on shifted arrays
    hh = pd.Series(hi).shift(1).rolling(ent).max().values
    ll = pd.Series(lo).shift(1).rolling(ent).min().values
    xh = pd.Series(hi).shift(1).rolling(ex).max().values
    xl = pd.Series(lo).shift(1).rolling(ex).min().values
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([hi - lo, np.abs(hi - pc), np.abs(lo - pc)]), axis=0)
    a = pd.Series(tr).rolling(atr_n).mean().values
    # D1 momentum, by D1 bar position
    dc = d1.close.values
    mom = np.full(len(dc), np.nan)
    mom[mom_n:] = dc[mom_n:] / dc[:-mom_n] - 1
    dd = d1.index.normalize().values
    hd = h.index.normalize().values
    if d1_mode == 'prevdate':
        # last D1 bar whose date is strictly before the H1 bar's date (closed before the H1 bar opened)
        k = np.searchsorted(dd, hd, side='left') - 1
    elif d1_mode == 'sameday_lookahead':   # deliberately WRONG: today's unfinished D1 bar
        k = np.searchsorted(dd, hd, side='right') - 1
    elif d1_mode == 'close_time':
        # decision at H1 close (open+1h): D1 bar of date X counts once the H1 bar closes at/after 24:00 of X,
        # i.e. the last H1 bar of the day may use that day's D1 bar (what an EA sees on the next bar's open)
        ht = (h.index + pd.Timedelta(hours=1)).values
        k = np.searchsorted(dd + np.timedelta64(1, 'D'), ht, side='right') - 1
    reg = np.where(k >= 0, mom[np.clip(k, 0, None)], np.nan)
    return dict(o=o, hi=hi, lo=lo, c=c, hh=hh, ll=ll, xh=xh, xl=xl, atr=a, reg=reg)


def run(h, ind, allow_long=True, allow_short=True, gate=True, swap_mult=1.0, spread=SPREAD, slip=SLIP,
        reverse_same_bar=True, stop_mult=2.5, sig=None):
    o, hi, lo, c = ind['o'], ind['hi'], ind['lo'], ind['c']
    n = len(o)
    dates = h.index.normalize()
    dow = h.index.dayofweek.values
    datev = dates.values
    reg = ind['reg']
    longsig = (c > ind['hh']) & ((reg > 0) if gate else True) & allow_long
    shortsig = (c < ind['ll']) & ((reg < 0) if gate else True) & allow_short
    if sig is not None:
        longsig = sig > 0; shortsig = sig < 0
    exl = c < ind['xl']; exs = c > ind['xh']
    trades = []
    pos = 0; ent = sl = 0.0; ei = -1
    for i in range(1, n):
        j = i - 1   # closed bar
        just_closed = False
        # 1) exit signal from closed bar j, at open of i
        if pos != 0 and j >= ei:
            if (pos == 1 and exl[j]) or (pos == -1 and exs[j]):
                px = o[i] - slip if pos == 1 else o[i] + spread + slip
                trades.append((ei, i, pos, ent, px, 'signal')); pos = 0; just_closed = True
        # 2) entry from closed bar j (flat, possibly right after a signal exit = close & reverse at same open)
        if pos == 0 and (reverse_same_bar or not just_closed):
            d_ = 1 if longsig[j] else (-1 if shortsig[j] else 0)
            if d_ != 0 and not np.isnan(ind['atr'][j]):
                ent = o[i] + spread + slip if d_ == 1 else o[i] - slip
                sl = ent - d_ * stop_mult * ind['atr'][j]
                pos = d_; ei = i
        # 3) stop during bar i (incl. entry bar)
        if pos == 1:
            if o[i] <= sl and ei != i:
                trades.append((ei, i, 1, ent, o[i] - slip, 'stop')); pos = 0
            elif lo[i] <= sl:
                trades.append((ei, i, 1, ent, min(sl, o[i]) - slip if ei != i else sl - slip, 'stop')); pos = 0
        elif pos == -1:
            ao, ah = o[i] + spread, hi[i] + spread
            if ao >= sl and ei != i:
                trades.append((ei, i, -1, ent, ao + slip, 'stop')); pos = 0
            elif ah >= sl:
                trades.append((ei, i, -1, ent, sl + slip, 'stop')); pos = 0
    # open position at end is left out (as an unfinished trade)
    rows = []
    for ei_, xi, dr, en, ex, why in trades:
        # nights: calendar date changes between entry bar and exit bar, triple when the night starts Wednesday
        nights = 0.0
        a_ = datev[ei_]; b_ = datev[xi]
        if b_ > a_:
            # only nights between consecutive *trading* dates are charged (weekend = one night, Fri)
            td = np.unique(datev[ei_:xi + 1])
            for k in range(1, len(td)):
                prev = pd.Timestamp(td[k - 1])
                nights += 3.0 if prev.dayofweek == 2 else 1.0
        g = (ex - en) if dr == 1 else (en - ex)
        sw = nights * (SWL if dr == 1 else SWS) * swap_mult
        rows.append(dict(entry_time=h.index[ei_], exit_time=h.index[xi], dir=dr, entry=round(en, 3), exit=round(ex, 3),
                         gross=g, swap=sw, pnl=g - sw, why=why, nights=nights))
    return pd.DataFrame(rows), pos


def daily(t, days):
    p = t.groupby(t.exit_time.dt.normalize()).pnl.sum() if len(t) else pd.Series(dtype=float)
    return p.reindex(days, fill_value=0.0)


def summ(t, days, label):
    p = daily(t, days); eq = p.cumsum(); m = p.groupby(p.index.to_period('M')).sum()
    tt = t[(t.exit_time >= days[0]) & (t.exit_time < days[-1] + pd.Timedelta(days=1))]
    return dict(window=label, per_day=round(p.mean(), 3), total=round(p.sum(), 1), max_dd=round((eq - eq.cummax()).min(), 0),
                losing_months=f'{(m < 0).sum()}/{len(m)}', days=len(p), trades=len(tt),
                win=round((tt.pnl > 0).mean() * 100, 1), longs=int((tt.dir == 1).sum()), shorts=int((tt.dir == -1).sum()),
                long_pnl=round(tt[tt.dir == 1].pnl.sum(), 0), short_pnl=round(tt[tt.dir == -1].pnl.sum(), 0),
                swap=round(tt.swap.sum(), 0))
