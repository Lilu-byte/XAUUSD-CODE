"""Shared loaders, signals and a bar-level backtester for XAUUSD intraday tests.

Prices are MT5 bid candles (server time GMT+2/+3). A position decided at a bar's
close earns the next bar's close-to-close return. Costs: half the bar's quoted
spread plus $0.10 slippage per unit of position change, and the broker's swap
(long -12.6 pts, short -4.6 pts per night, triple on Wednesday) on positions held
over the server's midnight.
"""
import numpy as np, pandas as pd

D = '/mnt/project-files/'
FILES = {'M5': D + 'xauusd-intraday/data/XAUUSD_M5.csv',
         'M15': D + 'xauusd-intraday/data/XAUUSD_M15.csv',
         'H1': D + 'xauusd-price-action/data/XAUUSD_H1.csv',
         'H4': D + 'xauusd-price-action/data/XAUUSD_H4.csv',
         'D1': D + 'xauusd-price-action/data/XAUUSD_D1.csv'}
MIN = {'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240, 'D1': 1440}
SLIP = 0.10
SWAP_LONG, SWAP_SHORT = 0.126, 0.046  # $ per oz per night


def load(tf):
    if tf == 'M30':
        m = load('M15')
        g = m.resample('30min', label='left', closed='left')
        d = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(),
                          'close': g.close.last(), 'spread': g.spread.mean()}).dropna()
        return d
    d = pd.read_csv(FILES[tf])
    d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    return d[['open', 'high', 'low', 'close', 'spread']].astype(float)


def ema(x, n):
    return x.ewm(span=n, adjust=False).mean()


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def hold(entry_long, exit_long, entry_short, exit_short):
    """Stateful position from boolean entry/exit series (+1/0/-1)."""
    el, xl, es, xs = (s.values for s in (entry_long, exit_long, entry_short, exit_short))
    p = np.zeros(len(el)); cur = 0
    for i in range(len(el)):
        if cur == 1 and xl[i]: cur = 0
        elif cur == -1 and xs[i]: cur = 0
        if cur == 0:
            if el[i]: cur = 1
            elif es[i]: cur = -1
        p[i] = cur
    return pd.Series(p, index=entry_long.index)


# ---- strategy families: each returns a position series in [-1, 1] ----
def s_ema(d, n):
    return np.sign(d.close - ema(d.close, n))


def s_cross(d, f, s):
    return np.sign(ema(d.close, f) - ema(d.close, s))


def s_donch(d, n):
    hi = d.high.rolling(n).max().shift(1); lo = d.low.rolling(n).min().shift(1)
    hx = d.high.rolling(n // 2).max().shift(1); lx = d.low.rolling(n // 2).min().shift(1)
    c = d.close
    return hold(c > hi, c < lx, c < lo, c > hx)


def s_meanrev(d, z):
    m = d.close.rolling(20).mean(); sd = d.close.rolling(20).std()
    zz = (d.close - m) / sd
    return hold(zz < -z, zz > 0, zz > z, zz < 0)


def s_rsi2(d, lvl):
    r = rsi(d.close, 2)
    return hold(r < lvl, r > 50, r > 100 - lvl, r < 50)


def grid():
    out = []
    for n in (20, 50, 100, 200): out.append((f'trend: price vs EMA{n}', lambda d, n=n: s_ema(d, n)))
    for f, s in ((10, 40), (20, 80), (50, 200)): out.append((f'trend: EMA{f}/{s} cross', lambda d, f=f, s=s: s_cross(d, f, s)))
    for n in (20, 55, 100): out.append((f'breakout: {n}-bar channel', lambda d, n=n: s_donch(d, n)))
    for z in (1.5, 2.0, 2.5): out.append((f'reversion: 20-bar z>{z}', lambda d, z=z: s_meanrev(d, z)))
    for l in (5, 10): out.append((f'reversion: RSI2<{l}', lambda d, l=l: s_rsi2(d, l)))
    res = []
    for name, f in out:
        res.append((name + ' (long+short)', f))
        res.append((name + ' (long only)', lambda d, f=f: f(d).clip(lower=0)))
    return res


def backtest(d, pos):
    """Return daily net returns (per unit notional) and trade stats."""
    pos = pos.reindex(d.index).fillna(0).clip(-1, 1)
    c = d.close
    ret = c.pct_change().shift(-1).fillna(0)          # next bar return
    turn = pos.diff().abs().fillna(pos.abs())
    cost = turn * (d.spread * 0.01 / 2 + SLIP) / c
    day = d.index.normalize()
    nxt = pd.Series(day, index=d.index).shift(-1)
    over = (nxt != day) & nxt.notna()
    mult = np.where(pd.Series(day, index=d.index).dt.dayofweek == 2, 3, 1)
    swap = over * mult * np.where(pos > 0, pos * SWAP_LONG, -pos * SWAP_SHORT) / c
    net = pos * ret - cost - swap
    daily = net.groupby(day).sum()
    return daily, turn.sum() / 2, pos.abs().mean()


def stats(daily, trades=None, expo=None):
    daily = daily[daily.index.dayofweek < 5]
    yrs = len(daily) / 252
    eq = (1 + daily).cumprod()
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else np.nan
    sh = daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else 0
    dd = (eq / eq.cummax() - 1).min()
    o = dict(ret_yr=cagr, sharpe=sh, max_dd=dd)
    if trades is not None: o['trades_yr'] = trades / yrs
    if expo is not None: o['exposure'] = expo
    return o


def align(d_hi, tf_hi, base_index, values):
    """Map a higher-timeframe series (indexed by bar open) onto a base timeline
    using only completed bars: a value becomes known at bar open + bar length."""
    s = pd.Series(np.asarray(values), index=d_hi.index + pd.Timedelta(minutes=MIN[tf_hi]))
    s = s[~s.index.duplicated(keep='last')]
    return s.reindex(s.index.union(base_index)).ffill().reindex(base_index)
