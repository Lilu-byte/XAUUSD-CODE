"""Backtest of the merged XAUUSD price-action rule set.

Data: OANDA XAUUSD hourly bid/ask (QuantConnect Lean sample data), 2006-03 .. 2019-02.
Everything is pure price action: swing pivots, close-based structure breaks,
candle anatomy. "Average range" is only used as a ruler for candle size and
proximity, never as a signal.
"""
import sys
import numpy as np
import pandas as pd

HOURLY = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/data/raw/hour/xauusd.csv"


def load_hourly(path):
    df = pd.read_csv(path, header=None)
    t = pd.to_datetime(df[0], format="%Y%m%d %H:%M")
    mid = pd.DataFrame({
        "o": (df[1] + df[6]) / 2, "h": (df[2] + df[7]) / 2,
        "l": (df[3] + df[8]) / 2, "c": (df[4] + df[9]) / 2,
        "spread": (df[9] - df[4]),
    })
    mid.index = t
    return mid


def resample(h1, rule):
    # shift +1h so the Sunday 23:00 open belongs to Monday and buckets match broker charts
    s = h1.copy()
    s.index = s.index + pd.Timedelta(hours=1)
    out = s.resample(rule).agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    out.index = out.index - pd.Timedelta(hours=1)  # label = bar open time in data tz
    return out


def structure(bars, k):
    """Close-based market structure. Returns per-bar arrays known at the bar's close."""
    h, l, c = bars.h.values, bars.l.values, bars.c.values
    n = len(bars)
    trend = np.zeros(n, int)          # +1 bull, -1 bear, 0 unknown
    event = np.zeros(n, int)          # +1/-1 when this bar's close broke structure
    last_sh = np.full(n, np.nan)      # most recent confirmed swing high level
    last_sl = np.full(n, np.nan)
    broken_lvl = np.full(n, np.nan)   # level of the swing broken by the latest BOS/CHoCH
    swings_h, swings_l = [], []       # (bar index, level) of confirmed pivots, for sweep checks
    cur_sh = cur_sl = np.nan
    sh_used = sl_used = True
    tr = 0
    blvl = np.nan
    sw_h_list = np.empty(n, object)
    sw_l_list = np.empty(n, object)
    for j in range(n):
        p = j - k  # pivot candidate confirmed at bar j
        if p - k >= 0:
            if h[p] == h[p - k:p + k + 1].max():
                cur_sh, sh_used = h[p], False
                swings_h.append((p, h[p]))
            if l[p] == l[p - k:p + k + 1].min():
                cur_sl, sl_used = l[p], False
                swings_l.append((p, l[p]))
        if not sh_used and c[j] > cur_sh:
            tr, sh_used, blvl = 1, True, cur_sh
            event[j] = 1
        elif not sl_used and c[j] < cur_sl:
            tr, sl_used, blvl = -1, True, cur_sl
            event[j] = -1
        trend[j], last_sh[j], last_sl[j], broken_lvl[j] = tr, cur_sh, cur_sl, blvl
        sw_h_list[j] = len(swings_h)
        sw_l_list[j] = len(swings_l)
    return dict(trend=trend, event=event, last_sh=last_sh, last_sl=last_sl,
                broken=broken_lvl, swings_h=swings_h, swings_l=swings_l,
                nh=sw_h_list, nl=sw_l_list)


def candle_signal(o, h, l, c, po, ph, pl, pc, avg):
    """+1 bullish / -1 bearish confirming candle, plus pattern name and pattern extreme."""
    rng = h - l
    if rng <= 0 or rng < 0.8 * avg:
        return 0, None, None
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    # rejection (pin) candles
    if lower >= 2 * body and lower >= 0.5 * rng and c >= l + 0.66 * rng:
        return 1, "bullish rejection", l
    if upper >= 2 * body and upper >= 0.5 * rng and c <= h - 0.66 * rng:
        return -1, "bearish rejection", h
    # engulfing (body engulfs prior body, closes beyond prior open, strong close)
    if pc < po and c > o and c >= po and o <= pc and body > abs(pc - po) and c >= l + 0.7 * rng:
        return 1, "bullish engulfing", min(l, pl)
    if pc > po and c < o and c <= po and o >= pc and body > abs(pc - po) and c <= h - 0.7 * rng:
        return -1, "bearish engulfing", max(h, ph)
    return 0, None, None


def find_setups(h4, d1, k_h4=2, k_d1=2, tol=0.5, sweep_lookback=30, daily_mode="agree",
                max_range_pos=0.5):
    S4 = structure(h4, k_h4)
    SD = structure(d1, k_d1)
    # daily state known at each H4 close = state of the last *completed* daily bar
    d_close_time = d1.index + pd.Timedelta(days=1)
    d_idx = np.searchsorted(d_close_time.values, (h4.index + pd.Timedelta(hours=4)).values, side="right") - 1
    o, hh, ll, cc = h4.o.values, h4.h.values, h4.l.values, h4.c.values
    avg = pd.Series(hh - ll).rolling(20).mean().shift(1).values
    out = []
    for j in range(25, len(h4)):
        tr = S4["trend"][j]
        if tr == 0 or np.isnan(avg[j]):
            continue
        dtr = SD["trend"][d_idx[j]] if d_idx[j] >= 0 else 0
        if daily_mode == "agree" and dtr != tr:
            continue
        if daily_mode == "not_against" and dtr == -tr:
            continue
        sig, name, ext = candle_signal(o[j], hh[j], ll[j], cc[j], o[j-1], hh[j-1], ll[j-1], cc[j-1], avg[j])
        if sig != tr:
            continue
        # --- location: near a prior swing, the broken level (retest) or beyond it (sweep)
        if tr == 1:
            refs = [S4["last_sl"][j], S4["broken"][j]]
            lo_rng, hi_rng = S4["last_sl"][j], np.nanmax(hh[max(0, j-60):j+1])
            pos = (ext - lo_rng) / (hi_rng - lo_rng) if hi_rng > lo_rng else 0.5
            near = any(not np.isnan(r) and ext <= r + tol * avg[j] for r in refs)
            # sweep: pattern traded through a confirmed swing low within lookback, closed back above
            sw = [lv for (p, lv) in S4["swings_l"][:S4["nl"][j]] if j - p <= sweep_lookback and p < j - 1]
            sweep = any(ext < lv < cc[j] for lv in sw)
        else:
            refs = [S4["last_sh"][j], S4["broken"][j]]
            hi_rng, lo_rng = S4["last_sh"][j], np.nanmin(ll[max(0, j-60):j+1])
            pos = (hi_rng - ext) / (hi_rng - lo_rng) if hi_rng > lo_rng else 0.5
            near = any(not np.isnan(r) and ext >= r - tol * avg[j] for r in refs)
            sw = [lv for (p, lv) in S4["swings_h"][:S4["nh"][j]] if j - p <= sweep_lookback and p < j - 1]
            sweep = any(cc[j] < lv < ext for lv in sw)
        if not near or pos > max_range_pos:
            continue
        risk = abs(cc[j] - ext)
        if risk <= 0:
            continue
        out.append(dict(time=h4.index[j], close_time=h4.index[j] + pd.Timedelta(hours=4), dir=tr,
                        pattern=name, entry=cc[j], invalidation=ext, risk=risk,
                        risk_x_avg=risk / avg[j], sweep=sweep, daily=dtr,
                        grade="A" if (sweep and dtr == tr) else ("B" if dtr == tr else "C")))
    return pd.DataFrame(out)


def score(setups, h1, max_hours=240):
    """Walk hourly bars after entry. Conservative: if one bar hits stop and target, it's a loss."""
    t = h1.index.values
    H, L, C = h1.h.values, h1.l.values, h1.c.values
    res = []
    for s in setups.itertuples():
        i0 = np.searchsorted(t, np.datetime64(s.close_time), side="left")
        if i0 + 5 >= len(t):
            res.append({}); continue
        d, e, stop, R = s.dir, s.entry, s.invalidation, s.risk
        row = {}
        for m in (1.0, 2.0):
            tgt = e + d * m * R
            outcome = None
            for i in range(i0, min(i0 + max_hours, len(t))):
                hit_stop = L[i] <= stop if d == 1 else H[i] >= stop
                hit_tgt = H[i] >= tgt if d == 1 else L[i] <= tgt
                if hit_stop:
                    outcome = 0; break
                if hit_tgt:
                    outcome = 1; break
            row[f"win_{m:g}R"] = outcome  # None = neither within 10 days
        # plain direction: is price on the right side of entry after 1 and 5 trading days
        for hrs, lab in ((24, "dir_1d"), (120, "dir_5d")):
            i = min(i0 + hrs - 1, len(t) - 1)
            row[lab] = int((C[i] - e) * d > 0)
        res.append(row)
    return pd.concat([setups.reset_index(drop=True), pd.DataFrame(res)], axis=1)


def summarize(df, label):
    def rate(col):
        x = df[col].dropna()
        return f"{100*x.mean():5.1f}% (n={len(x)})" if len(x) else "  n/a"
    print(f"{label:38s} setups={len(df):4d} | +1R before stop {rate('win_1R')} | "
          f"+2R before stop {rate('win_2R')} | right side 1d {rate('dir_1d')} | 5d {rate('dir_5d')}")


if __name__ == "__main__":
    h1 = load_hourly(HOURLY)
    h4 = resample(h1, "4h")
    d1 = resample(h1, "1D")
    d1 = d1[d1.index.dayofweek < 5]  # drop stray weekend stubs
    import pickle
    pickle.dump((h1, h4, d1), open("/home/claude/bt/bars.pkl", "wb"))
    print(len(h1), len(h4), len(d1))


def ltf_confirm(setups, h1, h4, wait=4):
    """Lower-timeframe timing: after the H4 setup candle closes, wait up to `wait` H1 candles
    for an H1 close beyond the setup candle's extreme in the trade direction (high for longs).
    Entry moves to that H1 close; setups that hit invalidation first or never confirm are dropped."""
    t = h1.index.values
    H, L, C = h1.h.values, h1.l.values, h1.c.values
    keep = []
    for s in setups.itertuples():
        bar = h4.loc[s.time]
        trig = bar.h if s.dir == 1 else bar.l
        i0 = np.searchsorted(t, np.datetime64(s.close_time), side="left")
        for i in range(i0, min(i0 + wait, len(t))):
            if (s.dir == 1 and L[i] <= s.invalidation) or (s.dir == -1 and H[i] >= s.invalidation):
                break
            if (C[i] - trig) * s.dir > 0:
                d = s._asdict(); d.pop("Index")
                d["entry"] = C[i]; d["risk"] = abs(C[i] - s.invalidation)
                d["close_time"] = pd.Timestamp(t[i]) + pd.Timedelta(hours=1)
                keep.append(d); break
    return pd.DataFrame(keep)
