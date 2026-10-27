"""Step 4: tail risk of pick C (M15 file, 2022-07..2026-10-09), concentration, bootstrap, news spikes,
and an M1-path replay of the M1-era trades (real M1 spreads, stop checked minute by minute)."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history')
from vlib import *
d = load('M15'); f, _ = features(d, 15); s = signal(d, f, 2, 4.0, 1); E = Eng(d, 15)
days, T = E.run(s, 2, 25, 3)
T['exit'] = d.index[T.xi.values]; T['ar'] = f.ar.values[T.ei.values]
SPL = pd.Timestamp('2025-01-01')
for nm, sel_d, sel_t in (('TRAIN', days.index < SPL, T.entry < SPL), ('TEST', days.index >= SPL, T.entry >= SPL), ('ALL', days.index >= days.index[0], T.entry >= T.entry.iloc[0])):
    p = days.pnl[sel_d]; t = T[sel_t.values]
    wk = p.groupby(p.index.to_period('W')).sum(); mo = p.groupby(p.index.to_period('M')).sum()
    # losing streaks
    def streak(x):
        b = 0; m = 0
        for v in x:
            b = b + 1 if v < 0 else 0; m = max(m, b)
        return m
    td = p[days.trades[sel_d] > 0]
    eq = p.cumsum(); dd = eq - eq.cummax()
    # longest time under water (calendar days)
    uw = 0; m_uw = 0; start = None
    for ts, v in dd.items():
        if v < 0:
            start = ts if start is None else start; m_uw = max(m_uw, (ts - start).days)
        else: start = None
    stops = t[t.pnl <= -24.5]
    print(f"{nm}: days {len(p)}, trades {len(t)}, {p.mean():+.3f}/d | worst day {p.min():+.2f} ({p.idxmin().date()}), worst trade {t.pnl.min():+.2f}, "
          f"worst week {wk.min():+.2f}, worst month {mo.min():+.2f}, best day {p.max():+.2f} | losing streak trades {streak(t.pnl.values)}, "
          f"trading days {streak(td.values)}, losing weeks in a row {streak(wk.values)} | max DD {dd.min():+.2f}, longest under water {m_uw} calendar days | "
          f"stop hits {len(stops)} ({len(stops) / max(len(t), 1):.3f} of trades) costing {stops.pnl.sum():+.1f}; same trades if stop had slipped $5 more: {-5 * len(stops):+.1f}")
    # concentration
    srt = np.sort(t.pnl.values)[::-1]
    print(f"   total {t.pnl.sum():+.1f}; without best 5 trades {t.pnl.sum() - srt[:5].sum():+.1f}, without best 10 {t.pnl.sum() - srt[:10].sum():+.1f}, "
          f"without best 5% ({int(len(srt) * .05)}) {t.pnl.sum() - srt[:int(len(srt) * .05)].sum():+.1f}; median trade {np.median(t.pnl):+.2f}")
    # weekly block bootstrap of $/day
    rng = np.random.default_rng(0); wkd = p.groupby(p.index.to_period('W'))
    blocks = [g.values for _, g in wkd]
    bs = []
    for _ in range(4000):
        pick = rng.integers(0, len(blocks), len(blocks)); x = np.concatenate([blocks[i] for i in pick]); bs.append(x.mean())
    bs = np.array(bs)
    print(f"   weekly block bootstrap $/day: 5% {np.percentile(bs, 5):+.3f}, 50% {np.percentile(bs, 50):+.3f}, 95% {np.percentile(bs, 95):+.3f}; P(<=0) {(bs <= 0).mean():.3f}")
# trades by hour of signal and the US-data window
T['hr'] = T.entry.dt.hour
g = T.groupby('hr').pnl.agg(['size', 'sum', 'mean'])
print('by signal hour (server): ' + ' '.join(f"{h}:{int(r['size'])}/{r['sum']:+.0f}" for h, r in g.iterrows()))
news = (T.entry.dt.hour * 60 + T.entry.dt.minute).between(15 * 60, 16 * 60 + 45)   # bars around 8:30/10:00 ET data
print(f"signal bars 15:00-16:45 server (US data window): {news.sum()} trades, {T.pnl[news].sum():+.1f} total, {T.pnl[news].mean():+.2f}/tr; "
      f"other hours {(~news).sum()} trades {T.pnl[~news].mean():+.2f}/tr; stop hits in window {int((T.pnl[news] <= -24.5).sum())} of {int((T.pnl <= -24.5).sum())}")
# signal size relative to the move: how big are the moves the rule fades? and the adverse excursion during the hold
h, l, o, c = d.high.values, d.low.values, d.open.values, d.close.values
mae = []
for _, t in T.iterrows():
    a, b = t.ei + 1, t.xi
    e = o[a]
    mae.append((e - l[a:b + 1].min()) if t.dir == 1 else (h[a:b + 1].max() - e))
T['mae'] = mae
mv = (d.close - d.close.shift(2)).values[T.ei.values]
print(f"faded 30-min move: median ${np.median(np.abs(mv)):.1f}, 90% ${np.percentile(np.abs(mv), 90):.1f}, max ${np.abs(mv).max():.1f}; "
      f"adverse excursion in the hold (M15 highs/lows): median ${np.median(T.mae):.1f}, 90% ${np.percentile(T.mae, 90):.1f}, 99% ${np.percentile(T.mae, 99):.1f}, max ${T.mae.max():.1f}")
for y in sorted(T.entry.dt.year.unique()):
    ty = T[T.entry.dt.year == y]
    print(f"   {y}: trades {len(ty)}, AR mean ${ty.ar.mean():.2f}, MAE>=25 {int((ty.mae >= 25).sum())}, stop hits {int((ty.pnl <= -24.5).sum())}, $/tr {ty.pnl.mean():+.2f}")
print('worst 5 days:', ', '.join(f"{i.date()} {v:+.1f} ({int(days.trades[i])} tr)" for i, v in days.pnl.nsmallest(5).items()))
# stacking: how often 2 positions are open at once
ov = 0
for i in range(1, len(T)):
    ov += int(T.ei.iloc[i] <= T.xi.iloc[i - 1])
print(f"trades opened while another pick-C trade was still open: {ov} of {len(T)}")

# --- news spikes in the M1 file: biggest 1-minute moves and what pick C did around them
m1 = load('M1')
r1 = (m1.high - m1.low)
top = r1.nlargest(12)
print('\nlargest M1 ranges (Jun 26 - Oct 9, 2026) and pick-C trades open within 60 min after:')
for ts, v in top.items():
    w = T[(T.entry <= ts + pd.Timedelta(minutes=60)) & (T.exit + pd.Timedelta(minutes=15) >= ts)]
    print(f"  {ts} range ${v:.1f} close-open {m1.close[ts] - m1.open[ts]:+.1f}: " + ('; '.join(f"sig {t.entry.strftime('%H:%M')} dir {t.dir:+d} pnl {t.pnl:+.1f}" for _, t in w.iterrows()) or 'no trade'))
# biggest 30-min moves in M5 history and pick-C reaction
m5 = load('M5'); mv30 = (m5.close - m5.close.shift(6)).abs()
print('largest 30-min moves on M5 (2025-05..2026-10) and pick-C trades within 2 h after:')
seen = []
for ts, v in mv30.sort_values(ascending=False).items():
    if any(abs((ts - x).total_seconds()) < 6 * 3600 for x in seen): continue
    seen.append(ts)
    w = T[(T.entry >= ts - pd.Timedelta(minutes=30)) & (T.entry <= ts + pd.Timedelta(hours=2))]
    print(f"  {ts} 30-min move ${v:.1f}: " + ('; '.join(f"sig {t.entry.strftime('%H:%M')} dir {t.dir:+d} pnl {t.pnl:+.1f}" for _, t in w.iterrows()) or 'no trade'))
    if len(seen) >= 10: break

# --- M1-path replay of the M1-era trades: entry at the M1 bar that opens the M15 bar i+1 (open + its M1 spread + $0.05),
#     stop $25 checked on M1 bars (gap through the stop exits at the M1 open), exit at the M1 close at the end of bar i+2.
mo_, mh, ml, mc = m1.open.values, m1.high.values, m1.low.values, m1.close.values
ms = m1.spread_usd.values + 0.05; mi = m1.index
TT = T[T.entry >= pd.Timestamp('2026-06-26')]
res = []
for _, t in TT.iterrows():
    t0 = t.entry + pd.Timedelta(minutes=15); t1 = d.index[t.xi] + pd.Timedelta(minutes=15)
    a = mi.searchsorted(t0); b = mi.searchsorted(t1) - 1
    if a >= len(mi) or mi[a] - t0 > pd.Timedelta(minutes=2): res.append(np.nan); continue
    dr = t.dir; e = mo_[a] + ms[a] if dr == 1 else mo_[a]; px = None
    for j in range(a, b + 1):
        if dr == 1:
            if mo_[j] <= e - 25: px = mo_[j]; break
            if ml[j] <= e - 25: px = e - 25; break
        else:
            if mo_[j] + ms[j] >= e + 25: px = mo_[j] + ms[j]; break
            if mh[j] + ms[j] >= e + 25: px = e + 25; break
    if px is None: px = mc[b] if dr == 1 else mc[b] + ms[b]
    res.append((px - e) * dr)
TT = TT.assign(m1pnl=res)
ok = TT.m1pnl.notna()
print(f"\nM1-path replay of the {len(TT)} M1-era trades ({ok.sum()} matched): M15 sim {TT.pnl[ok].sum():+.1f} total ({TT.pnl[ok].mean():+.2f}/tr), "
      f"M1 path {TT.m1pnl[ok].sum():+.1f} ({TT.m1pnl[ok].mean():+.2f}/tr); mean |diff| {np.abs(TT.pnl - TT.m1pnl)[ok].mean():.2f}; "
      f"entry spread (M1 bar) mean ${ms[mi.searchsorted(TT.entry + pd.Timedelta(minutes=15))].mean():.3f} vs M15 base ${(d.spread_usd.values[TT.ei.values + 1] + .05).mean():.3f}")
# stop-hit slippage evidence from M1: for M1-era bars where the M15 stop was hit, how far past the stop did the M1 bar go
T.to_csv('/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickC_trades_M15.csv', index=False)
