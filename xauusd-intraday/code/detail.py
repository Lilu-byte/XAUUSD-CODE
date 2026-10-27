"""Year-by-year, bootstrap vs buy-and-hold, and today's state for the leading
candidate: long only when the EMA20/80 trend is up on every timeframe."""
import pandas as pd, numpy as np
from lib import *

rng = np.random.default_rng(0)
for base, tfs in (('M15', ['M15', 'M30', 'H1', 'H4']), ('M5', ['M5', 'M15', 'M30', 'H1', 'H4'])):
    b = load(base); bc = b.index + pd.Timedelta(minutes=MIN[base])
    T = {tf: align(load(tf), tf, bc, s_cross(load(tf), 20, 80).values).fillna(0) for tf in tfs}
    up = pd.concat(T, axis=1).gt(0).all(1).astype(float); up.index = b.index
    dl, _, _ = backtest(b, up); bh, _, _ = backtest(b, pd.Series(1.0, index=b.index))
    df = pd.DataFrame({'strategy': dl, 'hold': bh}); df = df[df.index.dayofweek < 5]
    print(f'\n== base {base}: {tfs} ==')
    by = df.groupby(df.index.to_period('Q')).sum()
    print((by * 100).round(1).T.to_string())
    # stationary block bootstrap of Sharpe difference (blocks of 20 days)
    x = df.values; n = len(x); diffs = []
    for _ in range(2000):
        idx = np.concatenate([np.arange(s, s + 20) % n for s in rng.integers(0, n, n // 20 + 1)])[:n]
        y = x[idx]; s = y.mean(0) / y.std(0) * np.sqrt(252); diffs.append(s[0] - s[1])
    diffs = np.array(diffs)
    sh = df.mean() / df.std() * np.sqrt(252)
    print(f'Sharpe strategy {sh.strategy:.2f} vs hold {sh.hold:.2f}; P(strategy better) = {(diffs > 0).mean():.0%}; 90% CI of gap {np.percentile(diffs, 5):.2f}..{np.percentile(diffs, 95):.2f}')
    last = {tf: int(v.iloc[-1]) for tf, v in T.items()}
    print('state at last bar (9 Oct 2026 close):', last, '-> position', up.iloc[-1])
