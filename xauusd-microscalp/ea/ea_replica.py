"""Python replica of GoldMicroScalp.mq5, scored with mlib v2 (FAIR fills, base spread).
The signals are computed exactly as the EA computes them at the close of an M1 bar (checked bar by bar).
Trades are simulated as the EA places them: a signal at the close of M1 bar i enters at the open of
bar i+1 (the EA's first tick; long at open + spread, short at open), only if bar i+1 follows bar i
directly, only while the spread is at most InpMaxSpreadPts, and every module stops for the day once
the combined closed P&L reaches -InpDailyLoss.
Modules (EA input names in brackets):
  PB  [InpPB]  strong counter-trend N-minute candle -> enter WITH the H1 trend
  SF  [InpSF]  1-bar spike > 3x ATR240 moving away from the session VWAP -> fade it
  QB  [InpQB]  first M1 of a new M15 candle closes more than k x avg range(12 M15) beyond the previous
               M15 high/low -> fade (15:00-19:59)
  CP  [InpCP]  textbook candlestick patterns on M1 (net vote), optional H1 trend filter
Run: python3 ea_replica.py   (prints train/test per module and the default combination, writes expected_trades.csv)
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-candles/code')
from mlib import *
from patterns import detect
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea')
from ea_sim import _sim_next
from mlib import FILL, spread_series


def h1_trend(m):
    h1 = load('H1')
    return htf_on_m1(m, h1, 'H1', np.sign(ema(h1.close, 20) - ema(h1.close, 80)).values).fillna(0).values


def sig_pullback(m, trend, n=2, k=1.0, maru=0.9):
    c = resample(m, n)                                   # clock-aligned N-minute candles (label = open)
    body = (c.close - c.open).abs(); rng = c.high - c.low
    avg = body.shift(1).rolling(20).mean()
    colour = np.sign(c.close - c.open)
    hit = (body >= k * avg) & (body >= maru * rng) & (rng > 0)
    raw = pd.Series(np.where(hit, -colour, 0.0), index=c.index)        # direction = against the candle
    known = pd.Series(raw.values, index=c.index + pd.Timedelta(minutes=n))   # known when the candle closes
    at = m.index + pd.Timedelta(minutes=1)
    v = known.reindex(at).fillna(0).values                 # only on the M1 bar that completes the candle
    return np.where(v == trend, v, 0)                      # enter only WITH the H1 trend


def sig_spike_fade(m, mult=3.0):
    rng = m.high - m.low
    atr = rng.rolling(240).mean()
    day = m.index.normalize()
    tp = (m.high + m.low + m.close) / 3
    vw = (tp * m.tick_volume).groupby(day).cumsum() / m.tick_volume.groupby(day).cumsum()
    r1 = m.close.diff()
    up = (r1 > mult * atr) & (m.close > vw)
    dn = (r1 < -mult * atr) & (m.close < vw)
    return np.where(up, -1, np.where(dn, 1, 0)).astype(float)


def sig_quarter_fade(m, k=0.1, h0=15, h1=19):
    q = resample(m, 15)
    ar = (q.high - q.low).rolling(12).mean()
    prevh = pd.Series(q.high.values, index=q.index + pd.Timedelta(minutes=15))   # known after that candle closes
    prevl = pd.Series(q.low.values, index=q.index + pd.Timedelta(minutes=15))
    par = pd.Series(ar.values, index=q.index + pd.Timedelta(minutes=15))
    first = (m.index.minute % 15) == 0                       # first M1 bar of a new M15 candle
    # the previous closed M15 candle is the one that closed at this M1 bar's open time
    ph = prevh.reindex(m.index).values; pl = prevl.reindex(m.index).values; a = par.reindex(m.index).values
    hrs = (m.index.hour >= h0) & (m.index.hour <= h1)
    up = first & hrs & (m.close.values > ph + k * a)
    dn = first & hrs & (m.close.values < pl - k * a)
    return np.where(up, -1, np.where(dn, 1, 0)).astype(float)


def sig_patterns(m, trend, use_trend=True):
    P = detect(m[['open', 'high', 'low', 'close']])
    v = P['Any pattern (net vote)'].values
    return np.where(v == trend, v, 0) if use_trend else v


# EA defaults per module: (tp, sl, timeout minutes, max_open)
DEFAULTS = {'PB': (1.0, 5.0, 20, 3), 'SF': (0.5, 5.0, 5, 1), 'QB': (0.5, 2.0, 5, 1), 'CP': (0.5, 3.0, 5, 3)}

DAILY_LOSS = 15.0      # InpDailyLoss
MAX_SPREAD = 0.50      # InpMaxSpreadPts = 50 points on a 2-digit XAUUSD quote


def run_ea(H, s, tp, sl, timeout, max_open, spread='base'):
    """One module as the EA trades it (before the shared daily stop)."""
    m = H.m1
    s = np.sign(np.nan_to_num(np.asarray(s, float))).astype(np.int64)
    gap = np.r_[np.diff(m.index.values).astype('timedelta64[s]').astype(np.int64), 10**6]
    raw = spread_series(m, 'bar')
    nxt = np.r_[raw[1:], 99.0]
    s = np.where((gap == 60) & (nxt <= MAX_SPREAD), s, 0)            # fresh signal bar, spread filter at entry
    dp, dt, ti, to, tpn, tdr = _sim_next(H.o, H.h, H.l, H.c, H._spr[spread], H.tod, H.day, H.last, s,
                                         float(tp), float(sl), int(timeout), int(max_open), FILL['FAIR'], 0.0, 0.0, 0)
    return pd.DataFrame({'entry': m.index[ti], 'ei': ti, 'xi': np.where(to >= 0, to, ti), 'dir': tdr, 'pnl': tpn,
                         'bars': np.where(to >= 0, to - ti, -1)})


def daily_stop(T, limit=DAILY_LOSS):
    """Drop the trades the EA would not open once the day's combined closed P&L is at or below -limit."""
    if limit <= 0: return T
    out = []
    for d, g in T.groupby(T.entry.dt.normalize()):
        cum = 0.0; hb = None
        for xi, p in sorted(zip(g.xi, g.pnl)):
            cum += p
            if cum <= -limit: hb = xi; break
        out.append(g if hb is None else g[g.ei < hb])          # the EA checks the stop before that bar's entries
    return pd.concat(out)


def per_day(T, dates):
    return T.groupby(T.entry.dt.normalize()).pnl.sum().reindex(dates, fill_value=0.0)


def report(name, T, dates):
    p = per_day(T, dates)
    for per, sel in (('TRAIN', p.index < SPLIT), ('TEST', p.index >= SPLIT)):
        x = p[sel]; eq = x.cumsum(); tt = T[(T.entry >= SPLIT) == (per == 'TEST')]
        print(f"{name} {per}: {x.mean():+.2f}/day, {len(tt) / len(x):.1f} trades/day, win {(tt.pnl > 0).mean():.2f}, "
              f"per trade {tt.pnl.mean():+.3f}, days>=5 {(x >= 4.99).mean():.2f}, losing days {(x < 0).mean():.2f}, "
              f"worst day {x.min():+.1f}, maxDD {(eq - eq.cummax()).min():+.1f}")


if __name__ == '__main__':
    H = Harness(); m = H.m1; tr = h1_trend(m)
    S = {'PB': sig_pullback(m, tr), 'SF': sig_spike_fade(m), 'QB': sig_quarter_fade(m), 'CP': sig_patterns(m, tr)}
    allt = {}
    for k, s in S.items():
        tp, sl, to, mo = DEFAULTS[k]
        T = run_ea(H, s, tp, sl, to, mo); T['module'] = k; allt[k] = T
        rnd = np.mean([per_day(run_ea(H, random_like(s, z), tp, sl, to, mo), H.dates)[H.dates >= SPLIT].mean() for z in range(10)])
        report(f"{k} (TP {tp} SL {sl} hold {to}m max {mo}, no daily stop)", T, H.dates)
        print(f"   random directions on the same bars, TEST: {rnd:+.2f}/day")
    for combo in (['PB', 'SF', 'QB'], ['PB', 'SF', 'QB', 'CP']):
        T = pd.concat([allt[k] for k in combo]).sort_values('entry')
        report('+'.join(combo) + ' no daily stop', T, H.dates)
        report('+'.join(combo) + f' daily stop {DAILY_LOSS:.0f}', daily_stop(T), H.dates)
    T = daily_stop(pd.concat([allt[k] for k in ['PB', 'SF', 'QB']]).sort_values('entry'))
    T.drop(columns=['ei', 'xi']).to_csv('/mnt/project-files/xauusd-microscalp/ea/expected_trades.csv', index=False)
    print('expected_trades.csv:', len(T), 'trades (EA defaults: PB+SF+QB, daily stop, spread filter)')
