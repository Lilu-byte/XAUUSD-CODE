"""Verifier helpers: data via mlib (harness conventions), my own MR signal, grid wrapper and summaries."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/exits-stacking')
import numpy as np, pandas as pd
import mlib
from vgrid import grid_core

PATHS = {'FAIR': 0, 'FAIR4': 0, 'OHLC': 1, 'ADV': 2, 'FAIRO': 3, 'FAV': 4}
VOUT = '/mnt/project-files/xauusd-microscalp/verify/exits-stacking/'


def mr_signal(df, look=3, k=3.0, win=240):
    """fade |close[i]-close[i-look]| > k * mean(high-low over the last `win` bars incl. i). Known at close of bar i."""
    r = (df.close - df.close.shift(look)).values
    a = (df.high - df.low).rolling(win).mean().values
    s = np.where(np.abs(r) > k * a, -np.sign(r), 0.0)
    return np.nan_to_num(s).astype(np.int64)


class G:
    """Bar arrays for any timeframe frame with columns open/high/low/close/spread_usd/tod/last_of_session."""

    def __init__(self, df):
        self.df = df
        dates = df.index.normalize()
        u, inv = np.unique(dates.values, return_inverse=True)
        self.dates = pd.DatetimeIndex(u); self.day = inv.astype(np.int64)
        self.o, self.h, self.l, self.c = (df[k].values.astype(np.float64) for k in ('open', 'high', 'low', 'close'))
        self.tod = df.tod.values.astype(np.int64)
        self.last = df.last_of_session.values.astype(np.bool_)
        self.spr = {'bar': df.spread_usd.values.astype(np.float64), 'base': df.spread_usd.values + 0.05,
                    'wide': np.full(len(df), 0.30)}

    def run(self, sig, step=2.0, maxlev=50, btp=0.3, bsl=0.0, tmax=0, path='FAIR', spread='base', seed=0,
            gap_multi=False, first_tod=mlib.FIRST_ENTRY_TOD, last_tod=mlib.LAST_ENTRY_TOD, end_tod=mlib.END_TOD, spr=None):
        sig = np.sign(np.nan_to_num(np.asarray(sig, float))).astype(np.int64)
        sp = self.spr[spread] if spr is None else spr
        r = grid_core(self.o, self.h, self.l, self.c, sp, self.tod, self.day, self.last, sig, float(step), int(maxlev),
                      float(btp), float(bsl), int(tmax), PATHS[path], int(seed), int(first_tod), int(last_tod), int(end_tod),
                      bool(gap_multi))
        dp, dpos, dbsk, eql, levh, bs, be, bd, bl, bp, bw, bm = r
        days = pd.DataFrame({'pnl': dp, 'positions': dpos, 'baskets': dbsk}, index=self.dates)
        ix = self.df.index
        bask = pd.DataFrame({'start': ix[bs], 'end': ix[be], 'dir': bd, 'levels': bl, 'pnl': bp, 'why': bw, 'mae': bm,
                             'bars': be - bs})
        return days, bask, eql, levh


def summ(gg, days, bask, eql, levh, lo=None, hi=None):
    """Stats for days/baskets/bars with lo <= date < hi. Floating DD measured from equity at the window start."""
    ix = gg.df.index
    sd = np.ones(len(days), bool); sb = np.ones(len(bask), bool); sm = np.ones(len(ix), bool)
    if lo is not None:
        lo = pd.Timestamp(lo); sd &= days.index >= lo; sb &= (bask.start >= lo).values; sm &= ix >= lo
    if hi is not None:
        hi = pd.Timestamp(hi); sd &= days.index < hi; sb &= (bask.start < hi).values; sm &= ix < hi
    d = days[sd]; b = bask[sb]
    # equity before the window
    pre = days.pnl[days.index < lo].sum() if lo is not None else 0.0
    eq = eql[sm] - pre
    peak = np.maximum.accumulate(np.r_[0.0, eq])[1:] if len(eq) else eq
    eqc = d.pnl.cumsum()
    nd = max(len(d), 1)
    return dict(per_day=d.pnl.mean(), positions_day=d.positions.sum() / nd, baskets_day=d.baskets.sum() / nd,
                per_position=d.pnl.sum() / max(d.positions.sum(), 1), basket_win=(b.pnl > 0).mean() if len(b) else np.nan,
                days_ge5=(d.pnl >= 4.99).mean(), losing_days=(d.pnl < 0).mean(), worst_day=d.pnl.min(),
                max_dd_closed=(eqc - eqc.cummax()).min() if len(d) else np.nan,
                max_dd_float=(eq - peak).min() if len(eq) else np.nan, min_eq=eq.min() if len(eq) else np.nan,
                max_levels=int(levh[sm].max()) if sm.any() else 0, n_baskets=len(b), n_forced=int((b.why == 2).sum()),
                forced_pnl=float(b.pnl[b.why == 2].sum()), worst_basket=b.pnl.min() if len(b) else np.nan,
                total=d.pnl.sum(), days=len(d))


def load_m1_harness():
    m1 = mlib.load_m1()
    return m1, mlib.Harness(m1), G(m1)
