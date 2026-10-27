"""Pre-listed long/flat rules (all decided on closed D1 bars). Each returns a boolean 'want long' array."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/long-core')
from common import *

c = D1.close
H = D1.high; L = D1.low


def state(enter, exit_):
    enter = np.asarray(enter, bool); exit_ = np.asarray(exit_, bool)
    on = np.zeros(len(enter), bool); s = False
    for i in range(len(enter)):
        if not s and enter[i] and not exit_[i]: s = True
        elif s and exit_[i]: s = False
        on[i] = s
    return on


def above(n, kind='sma'):
    m = c.rolling(n).mean() if kind == 'sma' else c.ewm(span=n, adjust=False).mean()
    if kind == 'ema':
        m[:n] = np.nan   # warm-up
    return (c > m).values


def band(n, b):
    m = c.rolling(n).mean()
    return state((c > m * (1 + b)).values, (c < m * (1 - b)).values)


def vote(k, ns=(50, 100, 150, 200, 250)):
    v = sum((c > c.rolling(n).mean()).astype(int) for n in ns)
    ok = c.rolling(max(ns)).mean().notna()
    return ((v >= k) & ok).values


def golden(confirm=False):
    s50, s200 = c.rolling(50).mean(), c.rolling(200).mean()
    x = (s50 > s200)
    if confirm:
        x = x & (c > s200)
    return x.values


def mom(n):
    return (c > c.shift(n)).values


def mom_blend(ns=(21, 63, 126, 252)):
    v = sum((c > c.shift(n)).astype(int) for n in ns)
    return ((v >= 3) & c.shift(max(ns)).notna()).values


def donch(n, m):
    hi = c.rolling(n).max().shift(); lo = c.rolling(m).min().shift()
    return state((c > hi).values, (c < lo).values)


def asym(enter_n, exit_n):
    e = c > c.rolling(enter_n).mean(); x = c < c.rolling(exit_n).mean()
    return state(e.values, x.values)


def trend_pull():
    s100, s200 = c.rolling(100).mean(), c.rolling(200).mean()
    return state(((c > s100) & (s100 > s200)).values, (c < s200).values)


def rvol(n=20):
    return np.log(c).diff().rolling(n).std() * np.sqrt(252)


def volfilt(mode):
    base = above(200)
    v = rvol(20)
    if mode == 'pct80':
        lim = v.rolling(252).quantile(0.8)
        ok = (v < lim).values
    else:
        ok = (v < 0.30).values
    return base & ok


def giveback(k, rearm_n=50):
    """SMA200 long, but exit if close falls k*ATR(20) below the highest close since entry;
    after such a stop, re-enter only on a new rearm_n-day closing high while above SMA200."""
    s200 = c.rolling(200).mean().values
    a = gbt.atr(D1, 20).values
    hi = c.rolling(rearm_n).max().shift().values
    cv = c.values
    on = np.zeros(len(c), bool); s = False; stopped = False; peak = 0.0
    for i in range(len(c)):
        up = cv[i] > s200[i] if not np.isnan(s200[i]) else False
        if s:
            peak = max(peak, cv[i])
            if not up:
                s = False; stopped = False
            elif cv[i] < peak - k * a[i]:
                s = False; stopped = True
        else:
            if not up:
                stopped = False
            elif not stopped or (not np.isnan(hi[i]) and cv[i] > hi[i]):
                s = True; stopped = False; peak = cv[i]
        on[i] = s
    return on


def monthly(kind):
    me = pd.Series(D1.index.to_period('M'), index=D1.index)
    last = (me != me.shift(-1)).values.copy()
    last[-1] = False   # the final bar's month is not finished
    if kind == 'sma200':
        x = (c > c.rolling(200).mean()).astype(float)
    else:   # 10-month SMA of month-end closes
        mc = c[last]
        s10 = mc.rolling(10).mean()
        x = pd.Series(np.nan, index=D1.index); x[last] = (mc > s10).astype(float).values
    v = pd.Series(np.where(last, x, np.nan), index=D1.index)
    return v.ffill().fillna(0).values.astype(bool)


def catalog():
    R = {}
    for n in (50, 100, 150, 200, 250):
        R[f'sma{n}_daily'] = lambda n=n: above(n)
    for n in (50, 100, 150, 200, 250):
        R[f'sma{n}_friday'] = lambda n=n: friday_only(above(n))
    for n in (100, 200):
        R[f'ema{n}_daily'] = lambda n=n: above(n, 'ema')
    for b in (0.01, 0.02, 0.03):
        R[f'sma200_band{int(b*100)}'] = lambda b=b: band(200, b)
    R['sma100_band2'] = lambda: band(100, 0.02)
    for k in (2, 3, 4, 5):
        R[f'vote{k}of5_daily'] = lambda k=k: vote(k)
    for k in (2, 3, 4, 5):
        R[f'vote{k}of5_friday'] = lambda k=k: friday_only(vote(k))
    R['golden50_200'] = lambda: golden(False)
    R['golden50_200_closeabove'] = lambda: golden(True)
    for n in (63, 126, 252):
        R[f'mom{n}'] = lambda n=n: mom(n)
    R['mom_blend3of4'] = mom_blend
    for n, m in ((55, 20), (100, 50), (200, 100), (50, 25)):
        R[f'donch{n}_{m}'] = lambda n=n, m=m: donch(n, m)
    R['enter200_exit100'] = lambda: asym(200, 100)
    R['enter200_exit50'] = lambda: asym(200, 50)
    R['enter100up_exit200'] = trend_pull
    R['sma200_vol_pct80'] = lambda: volfilt('pct80')
    R['sma200_vol_lt30'] = lambda: volfilt('abs')
    for k in (4, 6, 8):
        R[f'sma200_giveback{k}atr'] = lambda k=k: giveback(k)
    R['monthly_sma200'] = lambda: monthly('sma200')
    R['monthly_10m'] = lambda: monthly('10m')
    return R
