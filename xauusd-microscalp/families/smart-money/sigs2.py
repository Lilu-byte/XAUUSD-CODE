"""Combined SMC entry models and filters (no look-ahead)."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from sigs import *
from mlib import htf_on_m1, ema, forming


@njit(cache=True)
def _sweep_then(o, h, l, c, N, W, conf, gmin):
    """Liquidity sweep of the prior N-bar low (wick below, close back above) arms a long for W bars;
    conf 0: enter at the first close above the sweep bar's high (displacement / micro-BOS);
    conf 1: enter at the first bullish FVG (low[j] - high[j-2] >= gmin) completed after the sweep;
    conf 2: wait for that FVG, then enter on the first retrace into it (close holding the gap).
    Mirror for shorts after a sweep of the N-bar high. A new low below the sweep low disarms."""
    n = len(c)
    s = np.zeros(n, np.int8)
    la = -1; lo_sw = 0.0; hi_sw = 0.0; lg_t = np.nan; lg_b = np.nan; lg = False
    sa = -1; hi_sw2 = 0.0; lo_sw2 = 0.0; sg_t = np.nan; sg_b = np.nan; sg = False
    for i in range(N + 2, n):
        # ---- long side progress (armed on an earlier bar)
        if la >= 0:
            if i - la > W or l[i] < lo_sw:
                la = -1
            elif conf == 0:
                if c[i] > hi_sw: s[i] = 1; la = -1
            elif conf == 1:
                if l[i] - h[i - 2] >= gmin and c[i] > c[i - 1]: s[i] = 1; la = -1
            else:
                if lg:
                    if l[i] <= lg_t:
                        if c[i] >= lg_b: s[i] = 1
                        la = -1; lg = False
                if la >= 0 and not lg and l[i] - h[i - 2] >= gmin:
                    lg = True; lg_t = l[i]; lg_b = h[i - 2]
        if sa >= 0:
            if i - sa > W or h[i] > hi_sw2:
                sa = -1
            elif conf == 0:
                if c[i] < lo_sw2: s[i] = -1 if s[i] == 0 else 0; sa = -1
            elif conf == 1:
                if l[i - 2] - h[i] >= gmin and c[i] < c[i - 1]: s[i] = -1 if s[i] == 0 else 0; sa = -1
            else:
                if sg:
                    if h[i] >= sg_t:
                        if c[i] <= sg_b: s[i] = -1 if s[i] == 0 else 0
                        sa = -1; sg = False
                if sa >= 0 and not sg and l[i - 2] - h[i] >= gmin:
                    sg = True; sg_t = h[i]; sg_b = l[i - 2]
        # ---- arm on this bar's sweep
        lo = l[i - 1]; hi = h[i - 1]
        for t in range(i - N, i - 1):
            if l[t] < lo: lo = l[t]
            if h[t] > hi: hi = h[t]
        if l[i] < lo and c[i] > lo:
            la = i; lo_sw = l[i]; hi_sw = h[i]; lg = False
        if h[i] > hi and c[i] < hi:
            sa = i; hi_sw2 = h[i]; lo_sw2 = l[i]; sg = False
    return s


def sweep_then(o, h, l, c, N, W, conf, gmin=0.0):
    return _sweep_then(o, h, l, c, int(N), int(W), int(conf), float(gmin))


def sweep_forming(m1, N, minutes=5, back=0.0):
    """'Before the candle ends': the FORMING M-minute candle has already pushed above the prior N closed
    M-bars' high and the M1 close is now back below that level by >= back -> short at that M1 close
    (first time per forming bar). Mirror for lows."""
    b = resample(m1, minutes)
    ph = b.high.rolling(N).max(); pl = b.low.rolling(N).min()
    key = m1.index.floor(f'{minutes}min')
    prev = key - pd.Timedelta(minutes=minutes)          # the closed bar right before the forming one
    PH = ph.reindex(prev).values; PL = pl.reindex(prev).values
    f = forming(m1, minutes)
    c = m1.close.values
    sh = (f.f_high.values > PH) & (c < PH - back)
    sl = (f.f_low.values < PL) & (c > PL + back)
    s = np.zeros(len(c), np.int8); s[sh] = -1; s[sl] = 1; s[sh & sl] = 0
    # first trigger per forming bar only
    ser = pd.Series(s, index=m1.index)
    first = ser.ne(0) & ~ser.ne(0).groupby(key).cumsum().gt(1)
    return np.where(first.values, s, 0).astype(np.int8)


# ---------------------------------------------------------------- filters
def sessions(m1):
    t = m1.tod.values
    return {'all': np.ones(len(t), bool), 'asia': (t >= 60) & (t < 600), 'lon': (t >= 600) & (t < 900),
            'ny': (t >= 900) & (t < 1140), 'late': t >= 1140}


def trend_m15(m1, n=20):
    b = resample(m1, 15)
    v = np.sign(b.close.values - ema(b.close, n).values)
    return np.nan_to_num(htf_on_m1(m1, b, 'M15', v).values)


def trend_h1(m1, n=20):
    b = resample(m1, 60)
    v = np.sign(b.close.values - ema(b.close, n).values)
    return np.nan_to_num(htf_on_m1(m1, b, 'H1', v).values)


def vol_regime(m1, n=14, look=1440):
    """+1 when the past-n-bar mean M1 range is above its own past-`look`-bar median, else -1."""
    r = (m1.high - m1.low)
    a = r.rolling(n).mean()
    med = a.rolling(look, min_periods=200).median()
    return np.where(a > med, 1, -1)
