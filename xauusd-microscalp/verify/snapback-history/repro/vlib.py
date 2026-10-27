"""Independent re-implementation of pick C (M15 snap-back fade, 30-min time exit, $25 disaster stop) from the
written rule text only. No import of the family's hlib/picks code.

Rule (as written by the colleague):
  AR32_i  = mean(high-low) of the 32 M15 bars before bar i (bars i-32..i-1)
  move_i  = close[i] - close[i-2], bars i-2, i-1, i consecutive (15-min steps)
  VWAP_i  = cumsum((H+L+C)/3 * tick_volume) / cumsum(tick_volume) from the day's first M15 bar (calendar day)
  SELL if move_i >  4*AR32_i and close_i > VWAP_i ; BUY if move_i < -4*AR32_i and close_i < VWAP_i
  entry at the first tick (open) of bar i+1 if it follows bar i directly and its spread <= 50 points;
  signal-bar open time 01:05..22:29, signal bar not the last of the session.
  No TP. Disaster stop $25. Exit at close of bar i+2. Force-close at 22:58 / session's last bar.
  Up to 3 open, one new per signal bar.

Simulator: own per-trade loop (positions do not interact: with a 2-bar hold at most 2 are open, so max_open=3
never binds; checked against ea_sim._sim_next in repro.py).
Prices: bid candles. Long enters at ask = open[i+1] + spr[i+1], exits at bid; short enters at bid = open[i+1],
exits at ask = bid + spr[exit bar]. Stop: long if bid low <= entry-25 (gap: open beyond stop -> exit at open);
short if ask high = high+spr >= entry+25.
"""
import numpy as np, pandas as pd

M15_FILE = '/mnt/project-files/xauusd-intraday/data/XAUUSD_M15.csv'
M5_FILE = '/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv'
M1_FILE = '/mnt/project-files/xauusd-microscalp/data/XAUUSD_M1.csv'
END_TOD = 22 * 60 + 58
FIRST, LAST = 65, 22 * 60 + 29
TRAIN = ('2022-07-01', '2025-01-01')
TEST = ('2025-01-01', '2026-10-10')


def load(path, step_min, zero_fill='hour'):
    d = pd.read_csv(path)
    d.index = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M')
    d = d[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].astype(float)
    d = d[d.index.dayofweek < 5].copy()
    sp = d.spread.copy(); z = sp <= 0
    if zero_fill == 'hour':                      # mlib convention: hour-of-day median of non-zero bars
        med = sp[~z].groupby(sp[~z].index.hour).median()
        sp[z] = d.index[z].hour.map(med).values
    elif zero_fill == 'month_hour':              # the family's convention
        key = d.index.to_period('M').astype(str) + '_' + d.index.hour.astype(str)
        mm = sp[~z].groupby(key[~z]).median(); mh = sp[~z].groupby(d.index.hour[~z]).median()
        f = pd.Series(key[z], index=d.index[z]).map(mm)
        f = f.fillna(pd.Series(d.index[z].hour, index=d.index[z]).map(mh))
        sp[z] = f.values
    d['spr_bar'] = sp.values * 0.01
    d['tod'] = d.index.hour * 60 + d.index.minute
    t = d.index.to_series()
    nxt = t.shift(-1)
    d['last'] = (((nxt - t) > pd.Timedelta(minutes=30)) | nxt.isna()).values
    d['step_prev'] = (t.diff() == pd.Timedelta(minutes=step_min)).values      # bar i follows i-1 directly
    d['step_next'] = ((nxt - t) == pd.Timedelta(minutes=step_min)).values     # bar i+1 follows i directly
    d['date'] = d.index.normalize()
    return d


def signal(d, k=4.0, L=32, n=2, gate=True):
    """+1 buy / -1 sell / 0, decided at the close of bar i from bars <= i only."""
    h, l, c, v = d.high.values, d.low.values, d.close.values, d.tick_volume.values
    rng = h - l
    cs = np.r_[0.0, np.cumsum(rng)]
    idx = np.arange(len(d))
    ar = np.full(len(d), np.nan)
    ok = idx >= L
    ar[ok] = (cs[idx[ok]] - cs[idx[ok] - L]) / L          # mean of bars i-L..i-1
    mv = np.full(len(d), np.nan); mv[n:] = c[n:] - c[:-n]
    st = d.step_prev.values
    consec = np.zeros(len(d), bool)
    consec[n:] = np.all(np.stack([st[n - j:len(d) - j] for j in range(n)]), axis=0)   # step at i, i-1, ..., i-n+1
    tp = (h + l + c) / 3
    day = d.date.values
    g = pd.Series(tp * v).groupby(day); gv = pd.Series(v).groupby(day)
    vw = (g.cumsum() / gv.cumsum()).values
    big_up = consec & (mv > k * ar); big_dn = consec & (mv < -k * ar)
    if gate:
        big_up &= c > vw; big_dn &= c < vw
    s = np.where(big_up, -1, np.where(big_dn, 1, 0))
    return s, ar, vw, mv


def eligible(d, max_spread=0.50):
    """EA entry conditions for a signal on bar i (entry at open of bar i+1)."""
    nxt_spr = np.r_[d.spr_bar.values[1:], 99.0]
    tod = d.tod.values
    return d.step_next.values & (nxt_spr <= max_spread + 1e-9) & (tod >= FIRST) & (tod <= LAST) & ~d.last.values


def trades(d, s, spr, N=2, sl=25.0, latency=0, stop_fill='exact', elig=None):
    """Per-trade simulation. Returns DataFrame (sig_i, entry time, dir, pnl, bars, exit_kind).
    latency: signal acted on `latency` bars later (entry at open of bar i+1+latency).
    stop_fill: 'exact' = at the stop price; 'extreme' = at the worst price of the bar (bid low for long,
    ask high for short) -- a slippage stress."""
    o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    tod = d.tod.values; last = d.last.values; day = d.date.values
    n = len(d)
    s = np.asarray(s).astype(int)
    if latency:
        s = np.r_[np.zeros(latency, int), s[:-latency]]
    if elig is None:
        elig = eligible(d)
    rows = []
    for i in np.where((s != 0) & elig)[0]:
        if i >= n - 1: continue
        dr = s[i]
        e = o[i + 1] + spr[i + 1] if dr == 1 else o[i + 1]
        px = None; kind = 'time'
        for j in range(i + 1, n):
            a = spr[j]
            stale = (j - i >= N) or (tod[j] >= END_TOD) or last[j] or (j == n - 1) or (day[j] != day[i])
            if day[j] != day[i]:
                px = o[j] if dr == 1 else o[j] + a; kind = 'daygap'; break
            if dr == 1:
                slp = e - sl
                if o[j] <= slp: px = o[j]; kind = 'stop_gap'; break
                if l[j] <= slp: px = (slp if stop_fill == 'exact' else l[j]); kind = 'stop'; break
                if stale: px = c[j]; kind = 'time' if j - i >= N else 'session'; break
            else:
                slp = e + sl
                if o[j] + a >= slp: px = o[j] + a; kind = 'stop_gap'; break
                if h[j] + a >= slp: px = (slp if stop_fill == 'exact' else h[j] + a); kind = 'stop'; break
                if stale: px = c[j] + a; kind = 'time' if j - i >= N else 'session'; break
        pnl = (px - e) if dr == 1 else (e - px)
        rows.append((i, d.index[i], dr, pnl, j - i, kind))
    return pd.DataFrame(rows, columns=['i', 'entry', 'dir', 'pnl', 'bars', 'kind'])


def per_day(T, dates):
    return T.groupby(T.entry.dt.normalize()).pnl.sum().reindex(dates, fill_value=0.0)


def stats(T, dates, lo, hi, extra=0.0):
    dd = dates[(dates >= pd.Timestamp(lo)) & (dates < pd.Timestamp(hi))]
    t = T[(T.entry >= pd.Timestamp(lo)) & (T.entry < pd.Timestamp(hi))]
    pnl = t.pnl - extra
    p = (t.assign(pnl=pnl).groupby(t.entry.dt.normalize()).pnl.sum()).reindex(dd, fill_value=0.0)
    eq = p.cumsum()
    nd = len(dd)
    return dict(per_day=p.mean(), trades_day=len(t) / nd, win=(pnl > 0).mean() if len(t) else np.nan,
                per_trade=pnl.mean() if len(t) else np.nan, days_ge5=(p >= 4.99).mean(),
                losing_days=(p < 0).mean(), worst_day=p.min(), worst_trade=pnl.min() if len(t) else np.nan,
                max_dd=(eq - eq.cummax()).min(), total=p.sum(), days=nd, trades=len(t),
                long_share=(t.dir == 1).mean() if len(t) else np.nan,
                t_trade=pnl.mean() / pnl.std(ddof=1) * np.sqrt(len(t)) if len(t) > 2 else np.nan)
