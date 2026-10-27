"""v2 (2026-10-14, after the harness audit in ../audit): positions close at the last bar of each
session (22:58 server or earlier), entries only 01:05-22:29, zero recorded spreads replaced by the
hour-of-day median, signals passed through np.sign. v1 kept as mlib_v1.py.

Shared harness for micro-scalping tests on XAUUSD M1 (one 0.01 lot = $1 per $1 move).

Data: MT5 export, bid candles, server time (GMT+3). M1 covers 2026-06-26..2026-10-09.
Split: TRAIN = up to 2026-08-31, TEST = 2026-09-01 onward. Pick rules on TRAIN only.

A signal decided at the close of M1 bar i (known at time index[i] + 1 minute) enters at that
close: long at ask = close + spread, short at bid = close. Exits are checked on later M1 bars
(i+1, i+2, ...): long exits at bid, short exits at ask = bid + spread of the exit bar.

Fill models when TP and SL are both inside the same M1 bar (common for $0.10-$1 brackets,
median M1 range is $1.70):
  FAIR  (1): random-walk odds from the bar open. The honest default.
  OHLC  (2): the path MT5's "1 minute OHLC" tester assumes: bullish bar O->L->H->C,
             bearish/flat bar O->H->L->C.
  STOP  (0): stop first (pessimistic).   TARGET (3): target first (optimistic, misleading).

Spread models: 'bar' = the bar's recorded spread (MT5 stores the lowest in the bar, so this is
optimistic), 'base' = bar spread + $0.05 (default), 'wide' = flat $0.30 (quote at export time).
"""
import sys, numpy as np, pandas as pd
from numba import njit

D = '/mnt/project-files/'
M1_FILE = D + 'xauusd-microscalp/data/XAUUSD_M1.csv'
OTHER = {'M5': D + 'xauusd-intraday/data/XAUUSD_M5.csv', 'M15': D + 'xauusd-intraday/data/XAUUSD_M15.csv',
         'H1': D + 'xauusd-price-action/data/XAUUSD_H1.csv', 'H4': D + 'xauusd-price-action/data/XAUUSD_H4.csv',
         'D1': D + 'xauusd-price-action/data/XAUUSD_D1.csv'}
MIN = {'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240, 'D1': 1440}
SPLIT = pd.Timestamp('2026-09-01')
FILL = {'STOP': 0, 'FAIR': 1, 'OHLC': 2, 'TARGET': 3}
END_TOD = 22 * 60 + 58      # v2: force-close at 22:58 server or the last bar of a session, whichever first
LAST_ENTRY_TOD = 22 * 60 + 29   # v2: no new entries after 22:29
FIRST_ENTRY_TOD = 1 * 60 + 5    # v2: no entries in the first 5 minutes after the 01:00 open (bad reopen prints)


def _read(path):
    d = pd.read_csv(path)
    d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    d = d[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].astype(float)
    return d[d.index.dayofweek < 5]


def load_m1():
    """M1 bars with spread in $ and time-of-day minutes."""
    d = _read(M1_FILE)
    sp = d.spread.copy()
    med = sp[sp > 0].groupby(sp[sp > 0].index.hour).median()
    zero = sp <= 0
    sp[zero] = d.index[zero].hour.map(med).values           # v2: 10% of bars (late Jun-early Jul) record 0
    d['spread_usd'] = sp * 0.01
    d['tod'] = d.index.hour * 60 + d.index.minute
    nxt = d.index.to_series().shift(-1)
    d['last_of_session'] = ((nxt - d.index.to_series()) > pd.Timedelta(minutes=30)) | nxt.isna()
    return d


def load(tf):
    if tf == 'M1': return load_m1()
    return _read(OTHER[tf])


def resample(m1, minutes):
    """Closed higher-timeframe candles built from M1 (label = bar open time)."""
    g = m1.resample(f'{minutes}min', label='left', closed='left')
    out = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(),
                        'close': g.close.last(), 'tick_volume': g.tick_volume.sum(), 'spread': g.spread.mean()})
    return out.dropna()


def forming(m1, minutes=5):
    """For each M1 bar: the partially formed higher-timeframe candle as known at that M1 close.
    Columns: f_open, f_high, f_low, f_close, f_minute (1..minutes = how many M1 bars are in)."""
    key = m1.index.floor(f'{minutes}min')
    g = m1.groupby(key)
    return pd.DataFrame({'f_open': g.open.transform('first'), 'f_high': g.high.cummax(), 'f_low': g.low.cummin(),
                         'f_close': m1.close, 'f_minute': g.cumcount() + 1}, index=m1.index)


def htf_on_m1(m1, d_hi, tf, values):
    """Map values computed on CLOSED higher-timeframe bars (indexed by bar open) onto the M1 timeline,
    as known at each M1 bar's close (index + 1 min). No look-ahead."""
    known = pd.Series(np.asarray(values, float), index=d_hi.index + pd.Timedelta(minutes=MIN[tf]))
    known = known[~known.index.duplicated(keep='last')]
    at = m1.index + pd.Timedelta(minutes=1)
    return pd.Series(known.reindex(known.index.union(at)).ffill().reindex(at).values, index=m1.index)


def ema(x, n):
    return x.ewm(span=n, adjust=False).mean()


def spread_series(m1, model='base'):
    s = m1.spread_usd.values.copy()
    if model == 'bar': return s
    if model == 'base': return s + 0.05
    if model == 'wide': return np.full(len(s), 0.30)
    raise ValueError(model)


@njit(cache=True)
def _sim(o, h, l, c, spr, tod, day, last, sig, tp, sl, timeout, max_open, fill, day_target, day_loss, cooldown):
    n = len(c)
    nd = day[-1] + 1
    dpnl = np.zeros(nd); dtr = np.zeros(nd)
    t_in = np.empty(n, np.int64); t_out = np.empty(n, np.int64); t_pnl = np.empty(n); t_dir = np.empty(n, np.int64)
    nt = 0
    pdir = np.zeros(max_open, np.int64); pent = np.zeros(max_open); pidx = np.full(max_open, -1, np.int64)
    pact = np.zeros(max_open, np.bool_); pslot = np.zeros(max_open, np.int64)
    cur = -1; dsum = 0.0; halted = False; last_entry = -1000000
    for i in range(n):
        if day[i] != cur:
            cur = day[i]; dsum = 0.0; halted = False
        # 1) exits on bar i for positions opened on earlier bars
        for k in range(max_open):
            if not pact[k] or pidx[k] >= i: continue
            e = pent[k]; s = pdir[k]; ex = False; px = 0.0
            a = spr[i]
            stale = (i - pidx[k] >= timeout) or (tod[i] >= END_TOD) or last[i] or (i == n - 1) or (day[i] != day[pidx[k]])
            if s == 1:
                tpp = e + tp; slp = e - sl
                if day[i] != day[pidx[k]]: px = o[i]; ex = True
                elif o[i] <= slp or o[i] >= tpp: px = o[i]; ex = True
                else:
                    hit_t = h[i] >= tpp; hit_s = l[i] <= slp
                    if hit_t and hit_s:
                        if fill == 0: px = slp
                        elif fill == 3: px = tpp
                        elif fill == 2:
                            px = slp if c[i] > o[i] else tpp
                        else:
                            q = (o[i] - slp) / (tpp - slp); px = q * tpp + (1 - q) * slp
                        ex = True
                    elif hit_t: px = tpp; ex = True
                    elif hit_s: px = slp; ex = True
                if not ex and stale: px = c[i]; ex = True
                pnl = px - e
            else:
                tpp = e - tp; slp = e + sl
                ao = o[i] + a; ah = h[i] + a; al = l[i] + a; ac = c[i] + a
                if day[i] != day[pidx[k]]: px = ao; ex = True
                elif ao >= slp or ao <= tpp: px = ao; ex = True
                else:
                    hit_t = al <= tpp; hit_s = ah >= slp
                    if hit_t and hit_s:
                        if fill == 0: px = slp
                        elif fill == 3: px = tpp
                        elif fill == 2:
                            px = tpp if c[i] > o[i] else slp
                        else:
                            q = (slp - ao) / (slp - tpp); px = q * tpp + (1 - q) * slp
                        ex = True
                    elif hit_t: px = tpp; ex = True
                    elif hit_s: px = slp; ex = True
                if not ex and stale: px = ac; ex = True
                pnl = e - px
            if ex:
                pact[k] = False
                j = pslot[k]
                t_out[j] = i; t_pnl[j] = pnl
                dpnl[day[pidx[k]]] += pnl
                if day[pidx[k]] == cur:
                    dsum += pnl
                    if (day_target > 0 and dsum >= day_target) or (day_loss > 0 and dsum <= -day_loss): halted = True
        # 2) entry at the close of bar i
        s = sig[i]
        if s != 0 and not halted and tod[i] <= LAST_ENTRY_TOD and tod[i] >= FIRST_ENTRY_TOD and not last[i] and i < n - 1 and i - last_entry >= cooldown:
            for k in range(max_open):
                if not pact[k]:
                    pact[k] = True; pdir[k] = s; pidx[k] = i; pslot[k] = nt
                    pent[k] = c[i] + spr[i] if s == 1 else c[i]
                    t_in[nt] = i; t_dir[nt] = s; t_out[nt] = -1; t_pnl[nt] = 0.0
                    nt += 1; dtr[day[i]] += 1; last_entry = i
                    break
    return dpnl, dtr, t_in[:nt], t_out[:nt], t_pnl[:nt], t_dir[:nt]


class Harness:
    """Holds M1 arrays once; run(signal, ...) returns per-day and per-trade results."""

    def __init__(self, m1=None):
        self.m1 = load_m1() if m1 is None else m1
        m = self.m1
        dates = m.index.normalize()
        u, inv = np.unique(dates.values, return_inverse=True)
        self.dates = pd.DatetimeIndex(u); self.day = inv.astype(np.int64)
        self.o, self.h, self.l, self.c = (m[k].values.astype(np.float64) for k in ('open', 'high', 'low', 'close'))
        self.tod = m.tod.values.astype(np.int64)
        self.last = m.last_of_session.values.astype(np.bool_)
        self._spr = {k: spread_series(m, k).astype(np.float64) for k in ('bar', 'base', 'wide')}

    def run(self, sig, tp, sl, timeout=10, max_open=1, fill='FAIR', spread='base',
            day_target=0.0, day_loss=0.0, cooldown=0):
        """sig: array of +1/-1/0 per M1 bar (decided at that bar's close).
        tp, sl: $ distances (0.01 lot: $1 per $1). timeout: bars to hold before closing at market.
        max_open: positions allowed at once (each signal bar opens at most one).
        day_target / day_loss: stop trading for the day at that closed P&L (0 = off)."""
        sig = np.sign(np.nan_to_num(np.asarray(sig, float))).astype(np.int64)   # v2: was a plain int cast
        dp, dt, ti, to, tpn, tdr = _sim(self.o, self.h, self.l, self.c, self._spr[spread], self.tod, self.day, self.last, sig,
                                        float(tp), float(sl), int(timeout), int(max_open), FILL[fill],
                                        float(day_target), float(day_loss), int(cooldown))
        days = pd.DataFrame({'pnl': dp, 'trades': dt}, index=self.dates)
        trades = pd.DataFrame({'entry': self.m1.index[ti], 'dir': tdr, 'pnl': tpn,
                               'bars': np.where(to >= 0, to - ti, -1)})
        return days, trades


def summarize(days, trades, period=None):
    """period: None (all), 'train' or 'test'."""
    if period == 'train':
        days = days[days.index < SPLIT]; trades = trades[trades.entry < SPLIT]
    elif period == 'test':
        days = days[days.index >= SPLIT]; trades = trades[trades.entry >= SPLIT]
    p = days.pnl; eq = p.cumsum(); nd = max(len(p), 1)
    return dict(per_day=p.mean(), trades_day=len(trades) / nd, win=(trades.pnl > 0).mean() if len(trades) else np.nan,
                per_trade=trades.pnl.mean() if len(trades) else np.nan, days_ge5=(p >= 4.99).mean(),
                losing_days=(p < 0).mean(), worst_day=p.min(), max_dd=(eq - eq.cummax()).min(), total=p.sum(), days=len(p))


def edge(m1, sig, horizons=(1, 2, 3, 5, 10), spread='base'):
    """Average move of the bid close in the signal's direction over the next k M1 bars, per signal,
    vs the average spread paid at those bars. Fill-model free: under any TP/SL bracket on a random
    walk, a trade loses the spread on average; only this directional move can pay for it."""
    sig = pd.Series(np.nan_to_num(np.asarray(sig, float)), index=m1.index)
    spr = pd.Series(spread_series(m1, spread), index=m1.index)
    rows = []
    for per, sel in (('train', m1.index < SPLIT), ('test', m1.index >= SPLIT)):
        m = (sig != 0) & sel
        ndays = len(np.unique(m1.index[sel].date))
        r = dict(period=per, signals_day=m.sum() / ndays, avg_spread=spr[m].mean())
        for k in horizons:
            f = ((m1.close.shift(-k) - m1.close) * sig)[m].dropna()
            r[f'move_{k}m'] = f.mean(); r[f'hit_{k}m'] = (f > 0).mean()
        rows.append(r)
    return pd.DataFrame(rows).set_index('period')


def random_like(sig, seed):
    """Same entry bars as sig, random direction: the luck baseline."""
    s = np.nan_to_num(np.asarray(sig, float))
    r = np.where(np.random.default_rng(seed).random(len(s)) < .5, 1, -1)
    return np.where(s != 0, r, 0)
