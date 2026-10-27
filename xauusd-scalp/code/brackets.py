"""Scalp brackets on M5: every signal bar opens one 0.01 lot at the bar close with take profit
TP and stop SL; closes at timeout (K bars) or 23:30 server. Up to MAXOPEN trades at once.
Spread is charged once per trade (long buys at bid+spread, exits at bid). If TP and SL are
both inside the same later bar, the stop is assumed to hit first."""
import sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from lib import load, ema, rsi, align
from numba import njit

@njit(cache=True)
def amb(tp, sl, spread, mode):
    # both levels inside one bar: 0 = stop first, 1 = random-walk odds, 2 = target first
    if mode == 0: return -sl
    if mode == 2: return tp
    p = max(0.0, min(1.0, (sl - spread) / (tp + sl)))
    return p * tp - (1 - p) * sl

@njit(cache=True)
def outcomes(h, l, c, tod, sig, tp, sl, spread, K, mode):
    n = len(c); pnl = np.zeros(n); exit_i = np.full(n, -1)
    for i in range(n - 1):
        s = sig[i]
        if s == 0 or tod[i] >= 23 * 60 + 15: continue
        if s > 0:
            e = c[i] + spread; tpp = e + tp; slp = e - sl
        else:
            e = c[i]; tpp = e - tp; slp = e + sl
        for j in range(i + 1, min(n, i + 1 + K)):
            if s > 0:
                a = h[j] >= tpp; b = l[j] <= slp
                if a and b: pnl[i] = amb(tp, sl, spread, mode); exit_i[i] = j; break
                if b: pnl[i] = -sl; exit_i[i] = j; break
                if a: pnl[i] = tp; exit_i[i] = j; break
            else:
                a = l[j] + spread <= tpp; b = h[j] + spread >= slp
                if a and b: pnl[i] = amb(tp, sl, spread, mode); exit_i[i] = j; break
                if b: pnl[i] = -sl; exit_i[i] = j; break
                if a: pnl[i] = tp; exit_i[i] = j; break
            if j == i + K or tod[j] >= 23 * 60 + 30 or j == n - 1:
                pnl[i] = (c[j] - e) if s > 0 else (e - c[j] - spread); exit_i[i] = j; break
    return pnl, exit_i

@njit(cache=True)
def cap(sig, exit_i, maxopen):
    n = len(sig); take = np.zeros(n, np.bool_); ends = np.full(maxopen, -1)
    for i in range(n):
        if sig[i] == 0 or exit_i[i] < 0: continue
        for k in range(maxopen):
            if ends[k] <= i:
                ends[k] = exit_i[i]; take[i] = True; break
    return take

d = load('M5'); d = d[d.index.dayofweek < 5]
c, o, h, l = d.close, d.open, d.high, d.low; body = c - o
tod = (d.index.hour * 60 + d.index.minute).values.astype(np.int64)
tr = {t: align(load(t), t, d.index, np.sign(ema(load(t).close, 20) - ema(load(t).close, 80)).values).fillna(0) for t in ('M15', 'H1', 'H4')}
m5t = np.sign(ema(c, 20) - ema(c, 80))
allup = (m5t > 0) & (tr['M15'] > 0) & (tr['H1'] > 0) & (tr['H4'] > 0)
alldn = (m5t < 0) & (tr['M15'] < 0) & (tr['H1'] < 0) & (tr['H4'] < 0)
same3 = (np.sign(body) == np.sign(body.shift(1))) & (np.sign(body) == np.sign(body.shift(2)))
r2 = rsi(c, 2)
SIG = {
    'coin flip': np.where(np.random.default_rng(1).random(len(d)) < .5, 1, -1),
    'always buy': np.ones(len(d)),
    'all agree (trend side)': np.where(allup, 1, np.where(alldn, -1, 0)),
    'all agree + pullback candle': np.where(allup & (body < 0), 1, np.where(alldn & (body > 0), -1, 0)),
    'fade 3 same-colour candles': -np.where(same3, np.sign(body), 0),
    'RSI2 extremes fade': np.where(r2 < 5, 1, np.where(r2 > 95, -1, 0)),
}
H, L, C = h.values, l.values, c.values
days_tr = len(np.unique(d.index[d.index < '2026'].date)); days_te = len(np.unique(d.index[d.index >= '2026'].date))
rows = []
for (name, s), tp, slm, spread, K, mo, mode in itertools.product(SIG.items(), (0.1, 0.25, 0.5, 1.0), (1, 3, 10, 30), (0.05, 0.15, 0.3), (12,), (1, 5, 1000), (0, 1, 2)):
    s = np.nan_to_num(np.asarray(s, float)); sl = tp * slm
    p, ex = outcomes(H, L, C, tod, s, tp, sl, spread, K, mode)
    t = cap(s, ex, mo)
    tr_m = t & (d.index < '2026'); te_m = t & (d.index >= '2026')
    dp = pd.Series(np.where(t, p, 0), index=d.index).groupby(d.index.date).sum()
    dte = dp[pd.to_datetime(dp.index) >= '2026']
    eq = dte.cumsum()
    rows.append(dict(fill=('stop first', 'random-walk odds', 'target first')[mode], signal=name, tp=tp, sl=sl, spread=spread, timeout_bars=K, max_open=mo,
                     tr_trades_day=tr_m.sum() / days_tr, tr_win=(p[tr_m] > 0).mean(), tr_per_day=p[tr_m].sum() / days_tr,
                     te_trades_day=te_m.sum() / days_te, te_win=(p[te_m] > 0).mean(), te_per_day=p[te_m].sum() / days_te,
                     te_worst_day=dte.min(), te_max_dd=(eq - eq.cummax()).min()))
g = pd.DataFrame(rows); g.to_csv('/mnt/project-files/xauusd-scalp/brackets.csv', index=False)
pd.set_option('display.width', 250)
print(len(g), 'combos. share with positive test $/day:'); print(g.pivot_table(index='spread', columns='fill', values='te_per_day', aggfunc=lambda x: (x > 0).mean()).round(3))
print('best test $/day per signal, fill = random-walk odds:')
f = g[g.fill == 'random-walk odds']
for sp in (0.05, 0.15, 0.3):
    x = f[f.spread == sp].sort_values('tr_per_day', ascending=False).groupby('signal').head(1)
    print('spread', sp); print(x[['signal', 'tp', 'sl', 'max_open', 'tr_per_day', 'te_trades_day', 'te_win', 'te_per_day', 'te_worst_day', 'te_max_dd']].round(2).to_string(index=False))
print('optimistic fill (target first) best by test $/day:')
print(g[g.fill == 'target first'].sort_values('te_per_day', ascending=False).head(8)[['signal', 'tp', 'sl', 'spread', 'max_open', 'te_trades_day', 'te_win', 'te_per_day']].round(2).to_string(index=False))
