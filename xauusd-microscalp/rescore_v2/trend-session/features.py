"""Feature table on the M1 timeline for the trend-session family. Every column is known at the
CLOSE of its M1 bar (uses bars <= i and higher-timeframe bars that had closed by then).
Cached to feats.pkl (small) so scans are fast."""
import os, sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'feats.pkl')


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(d, n):
    pc = d.close.shift(1)
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def nyao_scores(d):
    """Approximation of the Nyao scalper 0-10 trend score on closed bars of d (M5 by default).
    Components (buy side; sell side mirrors):
      range position in last 200 bars: >0.8 ->3, >0.65 ->2, >0.5 ->1
      (close-EMA200)/ATR14:              >2 ->3, >1 ->2, >0.3 ->1
      efficiency ratio over 100 bars, signed by direction: >0.3 ->2, >0.15 ->1
      192-bar momentum / ATR14:          >3 ->2, >1 ->1"""
    c = d.close
    hi = d.high.rolling(200).max(); lo = d.low.rolling(200).min()
    pos = (c - lo) / (hi - lo)
    a = atr(d, 14)
    dist = (c - ema(c, 200)) / a
    net = c - c.shift(100); path = c.diff().abs().rolling(100).sum()
    er = net / path
    mom = (c - c.shift(192)) / a

    def pts(x, cuts):  # cuts descending and nested: points = number of cuts exceeded
        return sum((x > t).astype(float) for t in cuts)

    def side(sgn):
        s = pts(sgn * (pos - 0.5) + 0.5, [0.8, 0.65, 0.5]) + pts(sgn * dist, [2, 1, 0.3]) + \
            pts(sgn * er, [0.3, 0.15]) + pts(sgn * mom, [3, 1])
        return np.where(np.isnan(pos) | np.isnan(mom) | np.isnan(er), np.nan, s)
    return side(1), side(-1)


def build():
    m1 = load_m1()
    f = pd.DataFrame(index=m1.index)
    c, o, h, l = m1.close, m1.open, m1.high, m1.low
    # higher-timeframe EMA20/EMA80 trend on closed bars
    src = {'M5': load('M5'), 'M15': load('M15'), 'H1': load('H1'), 'H4': load('H4')}
    m15 = src['M15']
    src['M30'] = m15.resample('30min', label='left', closed='left').agg(
        {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    for tf, d in src.items():
        e20, e80 = ema(d.close, 20), ema(d.close, 80)
        f['tr_' + tf] = htf_on_m1(m1, d, tf, np.sign(e20 - e80))
        f['ema20_' + tf] = htf_on_m1(m1, d, tf, e20)
    # Nyao score on M5 closed bars + D1 EMA50 filter
    nb, ns = nyao_scores(src['M5'])
    f['ny_buy'] = htf_on_m1(m1, src['M5'], 'M5', nb)
    f['ny_sell'] = htf_on_m1(m1, src['M5'], 'M5', ns)
    d1 = load('D1'); e50 = ema(d1.close, 50)
    d1up = (d1.close >= e50 * 1.005) & (e50 > e50.shift(1))
    d1dn = (d1.close <= e50 * 0.995) & (e50 < e50.shift(1))
    f['d1'] = htf_on_m1(m1, d1, 'D1', d1up.astype(float) - d1dn.astype(float))
    f['d1_side'] = htf_on_m1(m1, d1, 'D1', np.sign(d1.close - e50))
    # M1 features
    f['ema20_M1'] = ema(c, 20); f['ema50_M1'] = ema(c, 50)
    f['rsi3'] = rsi(c, 3); f['rsi7'] = rsi(c, 7); f['rsi14'] = rsi(c, 14)
    f['atr14'] = atr(m1, 14)
    red = (c < o).astype(int); grn = (c > o).astype(int)
    # consecutive red / green run lengths ending at bar i
    def run(x):
        g = (x != x.shift()).cumsum()
        return x.groupby(g).cumsum()
    f['nred'] = run(red); f['ngrn'] = run(grn)
    for n in (5, 10, 20, 60):
        f[f'hh{n}'] = h.shift(1).rolling(n).max()
        f[f'll{n}'] = l.shift(1).rolling(n).min()
    f['ret1'] = c.diff(); f['ret3'] = c.diff(3); f['ret5'] = c.diff(5)
    fm = forming(m1, 5)
    f['f5_open'] = fm.f_open; f['f5_min'] = fm.f_minute
    f['tod'] = m1.tod; f['spr'] = m1.spread_usd
    f['dow'] = m1.index.dayofweek
    f.to_pickle(CACHE)
    return f


def get():
    if os.path.exists(CACHE):
        return pd.read_pickle(CACHE)
    return build()


if __name__ == '__main__':
    f = build()
    print(f.shape)
    print(f.isna().mean().round(3)[f.isna().mean() > 0])
    tr = f[[c for c in f if c.startswith('tr_')]]
    print(tr.describe().round(2))
    print('nyao buy dist', pd.Series(f.ny_buy).value_counts().sort_index().to_dict())
    print('d1', f.d1.value_counts().to_dict())
