"""How far does gold move in the 1-6 M5 bars after each scalp signal, vs the spread?
Train May-Dec 2025, test Jan-Oct 2026. Moves in $ for one 0.01 lot ($1 per $1)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
from lib import load, ema, rsi, align
d = load('M5'); d = d[d.index.dayofweek < 5]
c, o, h, l = d.close, d.open, d.high, d.low
body = c - o; rng = (h - l).replace(0, np.nan)
tr = {}
for t in ('M15', 'H1', 'H4'):
    x = load(t); tr[t] = align(x, t, d.index, np.sign(ema(x.close, 20) - ema(x.close, 80)).values).fillna(0)
m5t = np.sign(ema(c, 20) - ema(c, 80))
allup = (m5t > 0) & (tr['M15'] > 0) & (tr['H1'] > 0) & (tr['H4'] > 0)
alldn = (m5t < 0) & (tr['M15'] < 0) & (tr['H1'] < 0) & (tr['H4'] < 0)
r2 = rsi(c, 2); atr = (h - l).rolling(50).mean()
sig = {  # +1 buy, -1 sell
    'last candle direction (follow)': np.sign(body),
    'last candle direction (fade)': -np.sign(body),
    '3 candles same colour (follow)': np.where((np.sign(body) == np.sign(body.shift(1))) & (np.sign(body) == np.sign(body.shift(2))), np.sign(body), 0),
    '3 candles same colour (fade)': -np.where((np.sign(body) == np.sign(body.shift(1))) & (np.sign(body) == np.sign(body.shift(2))), np.sign(body), 0),
    'big candle >2x avg (follow)': np.where((h - l) > 2 * atr, np.sign(body), 0),
    'big candle >2x avg (fade)': -np.where((h - l) > 2 * atr, np.sign(body), 0),
    'RSI2 <5 buy / >95 sell': np.where(r2 < 5, 1, np.where(r2 > 95, -1, 0)),
    'engulfing': np.where((body > 0) & (body.shift(1) < 0) & (c > o.shift(1)) & (o < c.shift(1)), 1, np.where((body < 0) & (body.shift(1) > 0) & (c < o.shift(1)) & (o > c.shift(1)), -1, 0)),
    'wick rejection (pin bar)': np.where((np.minimum(o, c) - l) > 0.6 * rng, 1, np.where((h - np.maximum(o, c)) > 0.6 * rng, -1, 0)),
    'all 4 timeframes agree': np.where(allup, 1, np.where(alldn, -1, 0)),
    'all agree + pullback candle': np.where(allup & (body < 0), 1, np.where(alldn & (body > 0), -1, 0)),
    'always buy': np.ones(len(d)),
}
rows = []
for name, s in sig.items():
    s = pd.Series(s, index=d.index).fillna(0)
    for k in (1, 3, 6):
        fwd = (c.shift(-k) - c) * s
        m = s != 0
        for per, sel in (('train', d.index < '2026-01-01'), ('test', d.index >= '2026-01-01')):
            f = fwd[m & sel].dropna()
            rows.append(dict(signal=name, bars=k, period=per, n_per_day=len(f) / len(np.unique(d.index[sel].date)),
                             avg_move=f.mean(), win=(f > 0).mean()))
r = pd.DataFrame(rows)
t = r.pivot_table(index=['signal', 'bars'], columns='period', values=['avg_move', 'win', 'n_per_day']).round(3)
pd.set_option('display.width', 250); print(t.to_string())
r.to_csv('/mnt/project-files/xauusd-scalp/edge.csv', index=False)
print('median quoted spread in bars 2026 ($):', (d.spread[d.index >= '2026'] * 0.01).median(), ' mean:', (d.spread[d.index >= '2026'] * 0.01).mean().round(3))
