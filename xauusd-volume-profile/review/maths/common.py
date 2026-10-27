import pandas as pd

FILES = {
    'M1': '/mnt/project-files/xauusd-microscalp/data/XAUUSD_M1.csv',
    'M5': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv',
    'M15': '/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv',
    'H1': '/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv',
    'H4': '/mnt/project-files/xauusd-price-action/data/XAUUSD_H4.csv',
}
_cache = {}


def load(tf):
    if tf not in _cache:
        d = pd.read_csv(FILES[tf])
        d['t'] = pd.to_datetime(d['time'], format='%Y.%m.%d %H:%M')
        _cache[tf] = d.set_index('t', drop=False)
    return _cache[tf]


def sel(tf, t0, t1):
    """Source candles CopyRates(src, from, to) returns: open time in [from, to] (to inclusive)."""
    d = load(tf)
    return d.loc[pd.Timestamp(t0):pd.Timestamp(t1)]


def resample(df, rule):
    g = df.resample(rule, label='left', closed='left').agg(
        {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'tick_volume': 'sum'}).dropna()
    return g[g['tick_volume'] > 0]
