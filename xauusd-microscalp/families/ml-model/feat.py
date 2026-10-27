"""Feature + target builder for the ML family. Every feature at M1 row i uses only bars <= i
(and higher-timeframe bars that had CLOSED by bar i's close, via htf_on_m1).
build(m1) -> DataFrame of float32 features indexed like m1.
targets(m1, k) -> forward bid move over k bars (NaN if the k-bar window crosses a gap/day)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
from mlib import load, forming, htf_on_m1, ema, MIN

EPS = 1e-9


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 * up / (up + dn + EPS)


def atr(df, n):
    pc = df.close.shift(1)
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=1).mean()


def shape(o, h, l, c, pref, F, norm):
    r = h - l
    F[pref + 'rng'] = r / norm
    F[pref + 'body'] = (c - o) / (r + EPS)
    F[pref + 'uw'] = (h - np.maximum(o, c)) / (r + EPS)
    F[pref + 'lw'] = (np.minimum(o, c) - l) / (r + EPS)


def build(m1, htf_cache=None):
    o, h, l, c, v = m1.open, m1.high, m1.low, m1.close, m1.tick_volume
    F = pd.DataFrame(index=m1.index)
    a14 = atr(m1, 14); a60 = atr(m1, 60)
    F['atr14'] = a14; F['atr_ratio'] = a14 / (a60 + EPS)
    # last 5 M1 candle shapes
    for j in range(5):
        shape(o.shift(j), h.shift(j), l.shift(j), c.shift(j), f'c{j}_', F, a14)
    F['up5'] = (c > o).astype(float).rolling(5).sum()
    F['up10'] = (c > o).astype(float).rolling(10).sum()
    # returns
    for k in (1, 2, 3, 5, 10, 15, 30, 60):
        F[f'ret{k}'] = (c - c.shift(k)) / a14
    d1 = c.diff()
    for n in (10, 30, 120):
        F[f'vol{n}'] = d1.rolling(n).std()
    F['vol10_120'] = F.vol10 / (F.vol120 + EPS)
    for n in (2, 7, 14):
        F[f'rsi{n}'] = rsi(c, n)
    for n in (10, 30, 120):
        mu = c.rolling(n).mean(); sd = c.rolling(n).std()
        F[f'z{n}'] = (c - mu) / (sd + EPS)
    for n in (5, 15, 60):
        hh = h.rolling(n).max(); ll = l.rolling(n).min()
        F[f'stoch{n}'] = (c - ll) / (hh - ll + EPS)
        F[f'hh{n}'] = (hh - c) / a14; F[f'll{n}'] = (c - ll) / a14
    # forming M5 / M15
    for mins in (5, 15):
        f = forming(m1, mins)
        p = f'f{mins}_'
        shape(f.f_open, f.f_high, f.f_low, f.f_close, p, F, a14)
        F[p + 'min'] = f.f_minute
        F[p + 'pos'] = (f.f_close - f.f_low) / (f.f_high - f.f_low + EPS)
    # closed higher-timeframe states (long history files for EMA warm-up)
    for tf in ('M5', 'M15', 'H1', 'H4'):
        d = load(tf) if htf_cache is None else htf_cache[tf]
        d = d[d.index < m1.index[-1] + pd.Timedelta(minutes=1)]
        e20 = ema(d.close, 20); e50 = ema(d.close, 50); at = atr(d, 14)
        vals = {'e20': e20, 'e50': e50, 'atr': at,
                'trend': (e20 - e50) / (at + EPS), 'slope': (e20 - e20.shift(3)) / (at + EPS),
                'rsi': rsi(d.close, 14), 'body': (d.close - d.open) / (d.high - d.low + EPS),
                'rng': (d.high - d.low) / (at + EPS),
                'uw': (d.high - np.maximum(d.open, d.close)) / (d.high - d.low + EPS),
                'lw': (np.minimum(d.open, d.close) - d.low) / (d.high - d.low + EPS),
                'ret3': (d.close - d.close.shift(3)) / (at + EPS)}
        mp = {k: htf_on_m1(m1, d, tf, x.values) for k, x in vals.items()}
        p = tf + '_'
        F[p + 'd20'] = (c - mp['e20']) / (mp['atr'] + EPS)
        F[p + 'd50'] = (c - mp['e50']) / (mp['atr'] + EPS)
        for k in ('trend', 'slope', 'rsi', 'body', 'rng', 'uw', 'lw', 'ret3'):
            F[p + k] = mp[k]
    # session / day context
    F['tod'] = m1.tod; F['dow'] = m1.index.dayofweek
    day = m1.index.normalize()
    g = m1.groupby(day)
    dop = g.open.transform('first'); dhi = g.high.cummax(); dlo = g.low.cummin()
    F['d_ret'] = (c - dop) / a14
    F['d_pos'] = (c - dlo) / (dhi - dlo + EPS)
    F['d_rng'] = (dhi - dlo) / a14
    # spread (recorded 0 before 2026-07-09 is a data gap -> NaN), tick volume
    s = m1.spread_usd.where(m1.spread > 0)
    F['spread'] = s; F['spread_rel'] = s / (s.rolling(60, min_periods=10).median() + EPS)
    vm = v.rolling(60, min_periods=10).median()
    F['tv0'] = v / (vm + EPS); F['tv1'] = v.shift(1) / (vm + EPS)
    F['tv5'] = v.rolling(5).sum() / (5 * vm + EPS)
    F['tv_body'] = F.tv0 * F.c0_body
    # round-number proximity
    F['rnd5'] = (c % 5) / 5; F['rnd10'] = (c % 10) / 10
    F = F.drop(columns=['atr14']).assign(atr14=a14)
    return F.astype(np.float32)


def targets(m1, k):
    c = m1.close
    fwd = c.shift(-k) - c
    ok = (m1.index.to_series().shift(-k) - m1.index.to_series()) == pd.Timedelta(minutes=k)
    return fwd.where(ok.values)


def cost(m1):
    """Base spread with the pre-2026-07-09 zero-spread gap imputed by the median ($0.14 + 0.05)."""
    s = m1.spread_usd.where(m1.spread > 0, 0.14)
    return s + 0.05


GROUPS = {
    'candle': lambda c: c.startswith(('c0_', 'c1_', 'c2_', 'c3_', 'c4_', 'up')),
    'ret': lambda c: c.startswith(('ret', 'vol', 'rsi', 'z', 'stoch', 'hh', 'll', 'atr')),
    'forming': lambda c: c.startswith(('f5_', 'f15_')),
    'htf': lambda c: c.startswith(('M5_', 'M15_', 'H1_', 'H4_')),
    'ctx': lambda c: c in ('tod', 'dow', 'd_ret', 'd_pos', 'd_rng', 'rnd5', 'rnd10'),
    'flow': lambda c: c.startswith(('spread', 'tv')),
}


def cols(F, groups):
    return [c for c in F.columns if any(GROUPS[g](c) for g in groups)]


def tradeable(m1):
    """Entry window: sessions run 01:00-22:59 server time and mlib's 23:30 force-close is never reached, so a
    position opened late would be carried over the daily break (gap + reopen spread). Enter only 01:05-22:39."""
    t = m1.tod.values
    return (t >= 65) & (t < 22 * 60 + 40)
