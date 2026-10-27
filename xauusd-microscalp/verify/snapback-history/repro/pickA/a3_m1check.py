"""(a) M15 file vs M15 built from M1 in the overlap; (b) recorded M15 spread vs M1 spread at the entry / exit minutes;
(c) re-simulate the pick's M1-era trades on M1 bars (stop checked minute by minute, M1 spreads);
(d) M15 file vs M15 built from M5 on the pick's best/worst days (data sanity of the days that carry the result)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/repro/pickA')
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/code')
from vA import *
from mlib import load_m1

d = load_m15(); s, ar = sig_A(d); S = Sim(d); days, T = S.run(s)
m1 = load_m1()
# (a) consistency in the overlap
g = m1.resample('15min', label='left', closed='left')
b = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(), 'close': g.close.last(),
                  'spread_min': g.spread.min(), 'spread_mean': g.spread.mean(), 'spread_first': g.spread.first(), 'n': g.open.count()}).dropna()
j = d.join(b, rsuffix='_m1', how='inner')
j = j[j.n == 15]
print(f"(a) overlap bars {len(j)}: |open diff| median {np.median(np.abs(j.open - j.open_m1)):.3f} p99 {np.quantile(np.abs(j.open - j.open_m1), .99):.3f}; "
      f"|close diff| p99 {np.quantile(np.abs(j.close - j.close_m1), .99):.3f}; high p99 {np.quantile(np.abs(j.high - j.high_m1), .99):.3f}")
jz = j[~j.raw_zero]
print(f"    M15 recorded spread (pts) median {jz.spread.median():.1f} vs min of its M1 spreads {jz.spread_min.median():.1f}, "
      f"mean of its M1 spreads {jz.spread_mean.median():.1f}, first M1 spread {jz.spread_first.median():.1f}; share M15 == M1 min {(jz.spread == jz.spread_min).mean():.2f}")
# (b) at the pick's entries and exits in the M1 era, and at all |move| > 2.5 AR bars (larger sample)
m1sp = m1.spread_usd
def m1_at(ts): return m1sp.reindex(ts).values
TT = T[T.entry >= m1.index[0]].copy()
ent_t = d.index[TT.ei.values + 1]; ex_t = d.index[TT.xi.values] + pd.Timedelta(minutes=14)
TT['m15_ent_sp'] = d.spread_usd.values[TT.ei.values + 1]; TT['m1_ent_sp'] = m1_at(ent_t)
TT['m15_ex_sp'] = d.spread_usd.values[TT.xi.values]; TT['m1_ex_sp'] = m1_at(ex_t)
print(f"(b) pick trades in M1 era: {len(TT)}; entry spread $ M15-recorded mean {TT.m15_ent_sp.mean():.3f} vs M1 bar at entry minute {np.nanmean(TT.m1_ent_sp):.3f}; "
      f"exit (shorts pay it) M15 {TT.m15_ex_sp.mean():.3f} vs M1 last minute {np.nanmean(TT.m1_ex_sp):.3f}")
c = d.close.values
mv = np.r_[np.nan, np.nan, c[2:] - c[:-2]]
big = (np.abs(mv) > 2.5 * ar) & (d.index >= m1.index[0]) & S.entry_ok()
ib = np.where(big)[0]; ib = ib[ib + 1 < len(d)]
e15 = d.spread_usd.values[ib + 1]; e1 = m1_at(d.index[ib + 1])
allb = np.where((d.index >= m1.index[0]))[0]; allb = allb[allb + 1 < len(d)]
print(f"    all |move|>2.5AR bars in M1 era ({len(ib)}): next-bar spread M15 {np.nanmean(e15):.3f} vs M1 entry minute {np.nanmean(e1):.3f} "
      f"(all bars: M15 {np.nanmean(d.spread_usd.values[allb + 1]):.3f} vs M1 {np.nanmean(m1_at(d.index[allb + 1])):.3f})")
# (c) re-simulate M1-era trades on M1 bars
mi = m1.index; mo_ = m1.open.values; mh = m1.high.values; ml = m1.low.values; mc = m1.close.values; msp = m1.spread_usd.values + 0.05
pos = pd.Series(np.arange(len(mi)), index=mi)
rows = []
for _, t in TT.iterrows():
    t_ent = d.index[t.ei + 1]; t_end = d.index[t.ei + 4] + pd.Timedelta(minutes=14)   # last M1 bar of bar i+4
    if t_ent not in pos.index: rows.append(np.nan); continue
    a = pos[t_ent]
    e = mo_[a] + msp[a] if t.dir == 1 else mo_[a]
    px = None
    k = a
    while True:
        if t.dir == 1:
            if ml[k] <= e - 25: px = min(mo_[k], e - 25) if k > a else e - 25; break
        else:
            if mh[k] + msp[k] >= e + 25: px = max(mo_[k] + msp[k], e + 25) if k > a else e + 25; break
        if mi[k] >= t_end or m1.last_of_session.values[k] or m1.tod.values[k] >= 22 * 60 + 58 or k == len(mi) - 1:
            px = mc[k] if t.dir == 1 else mc[k] + msp[k]; break
        k += 1
    rows.append(px - e if t.dir == 1 else e - px)
TT['pnl_m1'] = rows
print(f"(c) M1-era trades re-simulated on M1 bars: M15 sim total {TT.pnl.sum():+.2f} ({TT.pnl.mean():+.2f}/tr) vs M1 sim total {np.nansum(TT.pnl_m1):+.2f} "
      f"({np.nanmean(TT.pnl_m1):+.2f}/tr); per-trade |diff| median {np.nanmedian(np.abs(TT.pnl - TT.pnl_m1)):.2f} max {np.nanmax(np.abs(TT.pnl - TT.pnl_m1)):.2f}; missing {int(np.isnan(TT.pnl_m1).sum())}")
# (d) the days that carry the result, checked against M15 built from the M5 file
m5 = pd.read_csv('/mnt/project-files/xauusd-intraday/data/XAUUSD_M5.csv'); m5.index = pd.to_datetime(m5.time, format='%Y.%m.%d %H:%M')
g5 = m5.resample('15min', label='left', closed='left')
b5 = pd.DataFrame({'open': g5.open.first(), 'high': g5.high.max(), 'low': g5.low.min(), 'close': g5.close.last(), 'n': g5.open.count()}).dropna()
top = days.pnl[days.index >= pd.Timestamp('2025-05-05')].abs().sort_values(ascending=False).head(12).index
TB = T[T.entry.dt.normalize().isin(top)]
mx = 0.0; nb = 0
for _, t in TB.iterrows():
    for kk in range(t.ei - 2, t.xi + 1):
        ts = d.index[kk]
        if ts in b5.index and b5.n[ts] == 3:
            mx = max(mx, abs(d.open.values[kk] - b5.open[ts]), abs(d.high.values[kk] - b5.high[ts]), abs(d.low.values[kk] - b5.low[ts]), abs(d.close.values[kk] - b5.close[ts])); nb += 1
print(f"(d) {len(TB)} trades on the 12 largest |P&L| days since 2025-05: {nb} M15 bars compared with M5-built bars, max OHLC diff ${mx:.2f}")
print('    largest trades (signal time, dir, $, bars held, AR32, move):')
TT2 = T.copy(); TT2['ar'] = ar[T.ei.values]; TT2['move'] = mv[T.ei.values]
for _, t in TT2.reindex(TT2.pnl.abs().sort_values(ascending=False).index).head(8).iterrows():
    print(f"      {t.entry} {int(t.dir):+d} {t.pnl:+.2f} bars {int(t.bars)} AR {t.ar:.2f} move {t.move:+.2f}")
