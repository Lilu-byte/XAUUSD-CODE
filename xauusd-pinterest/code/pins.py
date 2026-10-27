"""Pinterest 1m-5m strategy families, coded with their published default settings (no tuning).
Run on XAUUSD M1 (2026-06-26..10-09) and M5 (2025-05-05..2026-10-09), one 0.01 lot.
Signals decided on a closed bar fill at the next bar's open (gbt engine)."""
import sys, numpy as np, pandas as pd
import gbt
S = '/tmp/claude-0/-home-user/d3a2884e-b5e1-564a-9afe-3f111e6d3946/scratchpad/data/'
gbt.FILES['M1'] = S + 'XAUUSD_M1.csv'; gbt.FILES['M5'] = S + 'XAUUSD_M5.csv'; gbt.FILES['M15'] = '/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv'
ema, rsi, macd, stoch, adx = gbt.ema, gbt.rsi, gbt.macd, gbt.stoch, gbt.adx


def cross_up(a, b): return (a > b) & (a.shift() <= b.shift())
def swing_sl(d, sig, n=10, floor=0.5):
    lo = d.low.rolling(n).min(); hi = d.high.rolling(n).max()
    dist = np.where(sig == 1, d.close - lo, np.where(sig == -1, hi - d.close, 0))
    return np.maximum(dist, floor)


def hma(x, n):
    def wma(s, k):
        w = np.arange(1, k + 1); return s.rolling(k).apply(lambda v: (v * w).sum() / w.sum(), raw=True)
    return wma(2 * wma(x, n // 2) - wma(x, n), int(np.sqrt(n)))


def heikin(d):
    hc = (d.open + d.high + d.low + d.close) / 4
    ho = hc.copy(); o = d.open.values; c = hc.values; h = np.empty(len(d)); h[0] = (o[0] + d.close.values[0]) / 2
    for i in range(1, len(d)): h[i] = (h[i - 1] + c[i - 1]) / 2
    return pd.Series(h, d.index), hc


def strategies(d):
    c = d.close; out = {}
    # 1. "3-EMA scalp" (25/50/100): stacked EMAs, pullback into EMA25-50 zone, close back beyond EMA25; SL past EMA100, TP 1.5R
    e25, e50, e100 = ema(c, 25), ema(c, 50), ema(c, 100)
    up = (e25 > e50) & (e50 > e100) & (d.low <= e25) & (c > e25) & (c > d.open) & (d.low > e100)
    dn = (e25 < e50) & (e50 < e100) & (d.high >= e25) & (c < e25) & (c < d.open) & (d.high < e100)
    sig = np.where(up, 1, np.where(dn, -1, 0)); sl = np.maximum(np.abs(c - e100), 0.5)
    out['3-EMA 25/50/100 pullback'] = dict(sig=sig, sl=sl, tp=1.5 * sl)
    # 2. Trend momentum scalp: EMA50 vs EMA100 trend, Stochastic(5,3,3) back above 20 / below 80; swing SL, 1.5R
    e50, e100 = ema(c, 50), ema(c, 100); k, _ = stoch(d, 5, 3, 3)
    sig = np.where((e50 > e100) & cross_up(k, pd.Series(20.0, d.index)), 1,
                   np.where((e50 < e100) & cross_up(pd.Series(80.0, d.index), k), -1, 0))
    sl = swing_sl(d, sig); out['EMA50/100 + Stochastic'] = dict(sig=sig, sl=sl, tp=1.5 * sl)
    # 3. "Momo" 5-min: close crosses EMA20 with MACD hist > 0 (or below/below); swing/EMA SL, half at 1R then MACD flip -> approximated as 1R target
    e20 = ema(c, 20); m, _ = macd(c)
    sig = np.where(cross_up(c, e20) & (m > 0), 1, np.where(cross_up(e20, c) & (m < 0), -1, 0))
    sl = swing_sl(d, sig); xl = (m < 0).values; xs = (m > 0).values
    out['Momo EMA20 + MACD'] = dict(sig=sig, sl=sl, exit_long=xl, exit_short=xs)
    # 4. EMA 9/55/200 + RSI 52/48; exit on opposite 9/55 cross; swing SL
    e9, e55, e200 = ema(c, 9), ema(c, 55), ema(c, 200); r = rsi(c)
    sig = np.where(cross_up(e9, e55) & (e55 > e200) & (r > 52), 1, np.where(cross_up(e55, e9) & (e55 < e200) & (r < 48), -1, 0))
    sl = swing_sl(d, sig); out['EMA 9/55/200 + RSI'] = dict(sig=sig, sl=sl, exit_long=(e9 < e55).values, exit_short=(e9 > e55).values)
    # 5. EMA 5/20 cross + MACD hist side + near Bollinger middle/lower; exit opposite cross
    e5, e20 = ema(c, 5), ema(c, 20); mid = c.rolling(20).mean(); sd = c.rolling(20).std(ddof=0)
    hist = m - m.ewm(span=9, adjust=False).mean()
    sig = np.where(cross_up(e5, e20) & (hist > 0) & (c < mid + sd), 1, np.where(cross_up(e20, e5) & (hist < 0) & (c > mid - sd), -1, 0))
    sl = swing_sl(d, sig); out['EMA 5/20 + MACD + Bollinger'] = dict(sig=sig, sl=sl, exit_long=(e5 < e20).values, exit_short=(e5 > e20).values)
    # 6. EMA 15/20 crossover, always in, reverse on opposite cross (plain pin rule)
    e15, e20 = ema(c, 15), ema(c, 20)
    sig = np.where(cross_up(e15, e20), 1, np.where(cross_up(e20, e15), -1, 0))
    out['EMA 15/20 crossover'] = dict(sig=sig, opp_exit=True)
    # 7. Gold "EMA 800" scalp: trade only with EMA800, enter on EMA 9/21 cross that way; swing SL, 1.5R
    e800, e9, e21 = ema(c, 800), ema(c, 9), ema(c, 21)
    sig = np.where(cross_up(e9, e21) & (c > e800), 1, np.where(cross_up(e21, e9) & (c < e800), -1, 0))
    sl = swing_sl(d, sig); out['Gold EMA800 trend + 9/21 cross'] = dict(sig=sig, sl=sl, tp=1.5 * sl)
    # 8. Heikin-Ashi + EMA: HA turns green above EMA50 (red below); exit when HA flips colour
    ho, hc = heikin(d); e50 = ema(c, 50); g = hc > ho
    sig = np.where(g & ~g.shift(fill_value=False) & (c > e50), 1, np.where(~g & g.shift(fill_value=False) & (c < e50), -1, 0))
    out['Heikin-Ashi + EMA50'] = dict(sig=sig, sl=swing_sl(d, sig), exit_long=(~g).values, exit_short=g.values)
    # 9. Hull(55) colour + DI cross, SL swing, TP 1R (axiory 1-minute list)
    h55 = hma(c, 55); _, pdi, mdi = adx(d); hup = h55 > h55.shift(2)
    sig = np.where(cross_up(pdi, mdi) & hup, 1, np.where(cross_up(mdi, pdi) & ~hup, -1, 0))
    sl = swing_sl(d, sig); out['Hull + ADX DI cross'] = dict(sig=sig, sl=sl, tp=sl)
    return out


def run(tf, spread, slip, start=None, end=None):
    d = gbt.load(tf); rows = []
    if start: d = d[start:end]
    for name, kw in strategies(d).items():
        kw = dict(kw); kw['sig'] = np.nan_to_num(np.asarray(kw['sig'], float)); kw['sig'][:1000] = 0   # indicator warm-up
        for key in ('sl', 'tp'):
            if key in kw: kw[key] = np.nan_to_num(np.asarray(kw[key], float))
        t = gbt.simulate(d, spread=spread, slip=slip, **kw)
        s = gbt.stats(t, d, name)
        p = gbt.daily(t, d); half = len(p) // 2
        s['1st_half'] = round(p.iloc[:half].mean(), 2); s['2nd_half'] = round(p.iloc[half:].mean(), 2)
        s['gross_per_trade'] = round(t.gross.mean() + spread + slip, 2) if len(t) else np.nan
        for dd, lab in ((1, 'long'), (-1, 'short')):
            s[lab + '_pnl'] = round(t.pnl[t.dir == dd].sum(), 0)
        sig = kw.pop('sig')
        cf = gbt.coinflip(d, sig, runs=30, spread=spread, slip=slip, **kw)
        s['random_dir_per_day'] = round(cf.mean(), 2); s['beats_random_%'] = round((cf < s['per_day']).mean() * 100)
        rows.append(s); print(tf, spread + slip, s, flush=True)
    return rows


if __name__ == '__main__':
    allr = []
    for tf, a, b in (('M1', None, None), ('M5', None, None), ('M15', '2022-07-01', '2025-05-04')):
        for sp, sl_ in ((0.30, 0.10), (0.15, 0.05)):
            for r in run(tf, sp, sl_, a, b):
                r.update(tf=tf if a is None else tf + ' 2022-07..2025-05', cost=sp + sl_); allr.append(r)
    pd.DataFrame(allr).to_csv(sys.argv[1], index=False)
