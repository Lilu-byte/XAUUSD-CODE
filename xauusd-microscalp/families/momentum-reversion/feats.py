"""Feature builder for the momentum / mean-reversion family. Everything at row i uses bars <= i only."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from mlib import *

A_SPLIT = pd.Timestamp('2026-08-01')   # internal TRAIN split: A = Jun26-Jul31, B = Aug


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d).clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def streak(sign):
    """Signed length of the run of same-sign values ending at i (0 for doji)."""
    s = np.asarray(sign); out = np.zeros(len(s))
    for i in range(len(s)):
        if s[i] == 0: out[i] = 0
        elif i > 0 and np.sign(out[i - 1]) == s[i]: out[i] = out[i - 1] + s[i]
        else: out[i] = s[i]
    return out


def build(m):
    f = pd.DataFrame(index=m.index)
    o, h, l, c, v = m.open, m.high, m.low, m.close, m.tick_volume
    f['body'] = c - o
    f['rng'] = h - l
    for k in (1, 2, 3, 5, 10):
        f[f'r{k}'] = c - c.shift(k)
    f['atr20'] = f.rng.rolling(20).mean()
    f['atr_prev20'] = f.rng.shift(1).rolling(20).mean()
    f['atr240'] = f.rng.rolling(240).mean()
    f['vreg'] = f.atr20 / f.atr240                                  # short vs long volatility
    f['atrq'] = f.atr20.rolling(1440 * 5, min_periods=1000).rank(pct=True)   # vol percentile vs last ~5 days
    f['streak'] = streak(np.sign(f.body.values))
    for n in (2, 3, 7):
        f[f'rsi{n}'] = rsi(c, n)
    for n in (10, 20, 30, 60):
        mu = c.rolling(n).mean(); sd = c.rolling(n).std()
        f[f'z{n}'] = (c - mu) / sd
        f[f'bbu{n}'] = (h - (mu + 2 * sd))        # >0: high pierced the upper 2sd band
        f[f'bbl{n}'] = ((mu - 2 * sd) - l)        # >0: low pierced the lower band
    # session VWAP since 01:00 server (bars before 01:00 belong to the previous session)
    sess = (m.index - pd.Timedelta(hours=1)).normalize()
    tp = (h + l + c) / 3
    cv = (tp * v).groupby(sess).cumsum(); cvol = v.groupby(sess).cumsum()
    f['vwap'] = cv / cvol
    f['vw_d'] = c - f.vwap
    f['vw_da'] = f.vw_d / f.atr20
    f['sess_bar'] = m.groupby(sess).cumcount()
    f['vol'] = v
    f['vrel'] = v / v.shift(1).rolling(60).median()
    f['rexp'] = f.rng / f.atr_prev20
    # inside bar: bar i-1 inside bar i-2; breakout at close of i beyond the mother bar (i-2)
    ib = (h.shift(1) <= h.shift(2)) & (l.shift(1) >= l.shift(2))
    f['ib_up'] = ib & (c > h.shift(2)); f['ib_dn'] = ib & (c < l.shift(2))
    f['ib_up2'] = ib & (c > h.shift(1)); f['ib_dn2'] = ib & (c < l.shift(1))
    # close location within the bar (0 = at low, 1 = at high)
    f['cloc'] = ((c - l) / f.rng.replace(0, np.nan)).fillna(.5)
    f['tod'] = m.tod
    f['spr'] = m.spread_usd
    return f


def fwd(m, ks=(1, 2, 3, 5, 10)):
    return {k: (m.close.shift(-k) - m.close).values for k in ks}


def valid_mask(m, f, guard=31):
    """Rows where an entry is allowed: features warmed up, not in the first 5 bars of the session, and at least
    `guard` minutes before that session's last bar (the data ends at 22:59 server, not 23:30, so mlib's END_TOD
    never fires; a position still open at the break would be closed at the reopen price - an artifact).
    With timeout <= 30 every position is closed inside its own session."""
    sess_day = m.index.normalize()
    last_tod = pd.Series(m.tod.values, index=m.index).groupby(sess_day).transform('max').values
    return ((m.tod.values <= last_tod - guard) & (f.sess_bar.values >= 5) & ~np.isnan(f.atr240.values))
