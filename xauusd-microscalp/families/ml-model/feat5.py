"""Features on M5 bars (long history 2025-05..) for a model that predicts the next 5/10 minutes at each
M5 close. Row t uses only M5 bars <= t (closed at t+5min) and HTF bars closed by then."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from feat import rsi, atr, shape, EPS, np, pd
from mlib import load, forming, ema, MIN


def map_closed(d_lo, d_hi, tf, values, lo_min=5):
    known = pd.Series(np.asarray(values, float), index=d_hi.index + pd.Timedelta(minutes=MIN[tf]))
    known = known[~known.index.duplicated(keep='last')]
    at = d_lo.index + pd.Timedelta(minutes=lo_min)
    return pd.Series(known.reindex(known.index.union(at)).ffill().reindex(at).values, index=d_lo.index)


def build5(d, cache=None):
    o, h, l, c, v = d.open, d.high, d.low, d.close, d.tick_volume
    F = pd.DataFrame(index=d.index)
    a14 = atr(d, 14); a48 = atr(d, 48)
    F['atr_ratio'] = a14 / (a48 + EPS)
    for j in range(5):
        shape(o.shift(j), h.shift(j), l.shift(j), c.shift(j), f'c{j}_', F, a14)
    F['up5'] = (c > o).astype(float).rolling(5).sum()
    for k in (1, 2, 3, 6, 12, 24):
        F[f'ret{k}'] = (c - c.shift(k)) / a14
    d1 = c.diff()
    for n in (12, 48):
        F[f'vol{n}'] = d1.rolling(n).std() / (a48 + EPS)
    for n in (2, 7, 14):
        F[f'rsi{n}'] = rsi(c, n)
    for n in (12, 48):
        mu = c.rolling(n).mean(); sd = c.rolling(n).std(); F[f'z{n}'] = (c - mu) / (sd + EPS)
    for n in (3, 12, 48):
        hh = h.rolling(n).max(); ll = l.rolling(n).min()
        F[f'stoch{n}'] = (c - ll) / (hh - ll + EPS); F[f'hh{n}'] = (hh - c) / a14; F[f'll{n}'] = (c - ll) / a14
    for mins in (15, 60):
        f = forming(d, mins); p = f'f{mins}_'
        shape(f.f_open, f.f_high, f.f_low, f.f_close, p, F, a14)
        F[p + 'n'] = f.f_minute; F[p + 'pos'] = (f.f_close - f.f_low) / (f.f_high - f.f_low + EPS)
    for tf in ('M15', 'H1', 'H4'):
        x = load(tf) if cache is None else cache[tf]
        x = x[x.index < d.index[-1] + pd.Timedelta(minutes=5)]
        e20 = ema(x.close, 20); e50 = ema(x.close, 50); at = atr(x, 14)
        vals = {'e20': e20, 'e50': e50, 'atr': at, 'trend': (e20 - e50) / (at + EPS),
                'slope': (e20 - e20.shift(3)) / (at + EPS), 'rsi': rsi(x.close, 14),
                'body': (x.close - x.open) / (x.high - x.low + EPS), 'ret3': (x.close - x.close.shift(3)) / (at + EPS)}
        mp = {kk: map_closed(d, x, tf, vv.values) for kk, vv in vals.items()}
        p = tf + '_'
        F[p + 'd20'] = (c - mp['e20']) / (mp['atr'] + EPS); F[p + 'd50'] = (c - mp['e50']) / (mp['atr'] + EPS)
        for kk in ('trend', 'slope', 'rsi', 'body', 'ret3'):
            F[p + kk] = mp[kk]
    F['tod'] = d.index.hour * 60 + d.index.minute; F['dow'] = d.index.dayofweek
    day = d.index.normalize(); g = d.groupby(day)
    dop = g.open.transform('first'); dhi = g.high.cummax(); dlo = g.low.cummin()
    F['d_ret'] = (c - dop) / a14; F['d_pos'] = (c - dlo) / (dhi - dlo + EPS); F['d_rng'] = (dhi - dlo) / a14
    vm = v.rolling(48, min_periods=10).median()
    F['tv0'] = v / (vm + EPS); F['tv1'] = v.shift(1) / (vm + EPS); F['tv_body'] = F.tv0 * F.c0_body
    return F.astype(np.float32)


def targets5(d, n):
    fwd = d.close.shift(-n) - d.close
    t = d.index.to_series()
    return fwd.where(((t.shift(-n) - t) == pd.Timedelta(minutes=5 * n)).values)
