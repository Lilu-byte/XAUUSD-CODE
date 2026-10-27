"""Step 4: tail risk of pick A on a $3,000 account (0.01 lot, $1 per $1).
 worst day / trade / week / month, streaks, drawdown, stops (count, cost, AR units), stacking, news-hour trades,
 M1/M5 replays with pessimistic stop fills, the largest 1-minute spikes, day-bootstrap of a year."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickA')
from alib import *
ACC = 3000.0
d = finish(read('M15')); E = Eng(d, 15); f = features(d, 15); s = signal(d, f)
days, T = E.run(s, 4, 25, 3)
T['exit'] = d.index[T.xi.values]; T['ar'] = f.ar.values[T.ei.values]; T['year'] = T.entry.dt.year
P = {'TRAIN': ('2022-07-01', '2025-01-01'), 'TEST': ('2025-01-01', None), 'ALL': ('2022-07-01', None)}


def streak(x):
    best = cur = 0
    for v in x:
        cur = cur + 1 if v else 0; best = max(best, cur)
    return best


for p, (lo, hi) in P.items():
    dd = days[(days.index >= lo) & ((days.index < hi) if hi else True)].pnl
    tt = T[(T.entry >= lo) & ((T.entry < hi) if hi else True)]
    wk = dd.groupby(dd.index.to_period('W')).sum(); mn = dd.groupby(dd.index.to_period('M')).sum()
    eq = dd.cumsum(); dd_ = eq - eq.cummax()
    under = (dd_ < 0).astype(int); longest_under = streak(under.values)
    tdays = dd[days.trades.reindex(dd.index) > 0]
    print(f"{p}: worst day {dd.min():+.1f} ({dd.idxmin().date()}), worst trade {tt.pnl.min():+.1f}, worst week {wk.min():+.1f} ({wk.idxmin()}), "
          f"worst month {mn.min():+.1f} ({mn.idxmin()}), losing months {int((mn < 0).sum())}/{len(mn)}, longest losing-trade streak {streak(tt.pnl.values < 0)}, "
          f"longest run of losing trading days {streak(tdays.values < 0)}, max DD {dd_.min():+.1f} = {100 * dd_.min() / ACC:.1f}% of $3,000, "
          f"longest time under water {longest_under} trading days, days with loss <= -25: {int((dd <= -25).sum())}, <= -50: {int((dd <= -50).sum())}")
# stops
print('\nstops by year: trades, stops hit, stop share, total lost on stop trades, $25 stop in AR units (median), AR median')
for y, g in T.groupby('year'):
    st = g.pnl <= -24.5
    print(f"  {y}: {len(g)} trades, {int(st.sum())} stops ({st.mean():.2f}), {g.pnl[st].sum():+.0f} on them, stop = {np.median(25 / g.ar):.1f} AR, AR ${g.ar.median():.2f}")
d0, T0 = E.run(s, 4, 1000, 3)                                                         # same trades without the stop
T0 = T0.set_index('ei'); Ts = T.set_index('ei')
com = Ts.index.intersection(T0.index)
hit = Ts.loc[com].pnl <= -24.5
diff = (Ts.loc[com].pnl - T0.loc[com].pnl)[hit]
for p, (lo, hi) in P.items():
    m = hit & (Ts.loc[com].entry >= lo) & ((Ts.loc[com].entry < hi) if hi else True)
    print(f"  {p}: stop-hit trades {int(m.sum())}; the same trades held to the time exit would have made {T0.loc[com][m].pnl.sum():+.0f} "
          f"(worst {T0.loc[com][m].pnl.min():+.1f}) vs {Ts.loc[com][m].pnl.sum():+.0f} with the stop -> stop's net effect {(Ts.loc[com][m].pnl - T0.loc[com][m].pnl).sum():+.0f}")
print(f"  no-stop version worst trade overall {T0.pnl.min():+.1f} on {d.index[T0.pnl.idxmin()]}, trades worse than -25 without stop {int((T0.pnl < -25).sum())}, worse than -40 {int((T0.pnl < -40).sum())}")
# stacking
ev = []
for _, r in T.iterrows(): ev += [(r.ei, 1), (r.xi, -1)]
ev.sort(key=lambda x: (x[0], x[1])); cur = 0; mx = 0; cnt = {1: 0, 2: 0, 3: 0}
for _, e in ev:
    cur += e; mx = max(mx, cur)
    if e == 1: cnt[cur] = cnt.get(cur, 0) + 1
grp = T.groupby(T.entry.dt.normalize())
same_dir = 0; worst_stack = 0.0
for _, g in grp:
    if len(g) < 2: continue
    gi = g.sort_values('ei')
    for i in range(len(gi)):
        ov = gi[(gi.ei <= gi.ei.iloc[i]) & (gi.xi > gi.ei.iloc[i])]
        if len(ov) >= 2: worst_stack = min(worst_stack, ov.pnl.sum()); same_dir += int(ov.dir.nunique() == 1 and len(ov) == 3)
print(f"\nstacking: entries made while 1/2/3 positions open (incl. itself): {cnt}; max simultaneous {mx}; worst combined P&L of an overlapping stack {worst_stack:+.1f}")
# news windows (server time; US 08:30 ET releases = 15:30 server, FOMC 14:00 ET = 21:00 server)
hh = T.entry.dt.hour * 60 + T.entry.dt.minute
win = {'US data 15:15-16:00': (hh >= 915) & (hh <= 960), 'FOMC 20:45-21:30': (hh >= 1245) & (hh <= 1290)}
win['other'] = ~(win['US data 15:15-16:00'] | win['FOMC 20:45-21:30'])
for k, m in win.items():
    g = T[m]
    print(f"  signal bar in {k}: {len(g)} trades ({len(g) / len(T):.2f}), {g.pnl.mean():+.2f}/tr, total {g.pnl.sum():+.0f}, stops {int((g.pnl <= -24.5).sum())}, worst {g.pnl.min():+.1f}")
nfp = T[(T.entry.dt.dayofweek == 4) & (T.entry.dt.day <= 7) & win['US data 15:15-16:00']]
print(f"  first-Friday (NFP) 15:15-16:00 trades: {len(nfp)}, {nfp.pnl.mean():+.2f}/tr, total {nfp.pnl.sum():+.0f}, stops {int((nfp.pnl <= -24.5).sum())}")
print('  10 worst trades:', '; '.join(f"{r.entry:%Y-%m-%d %H:%M} {'L' if r.dir == 1 else 'S'} {r.pnl:+.1f} (AR {r.ar:.1f})" for _, r in T.nsmallest(10, 'pnl').iterrows()))
print('  10 best trades:', '; '.join(f"{r.entry:%Y-%m-%d %H:%M} {'L' if r.dir == 1 else 'S'} {r.pnl:+.1f}" for _, r in T.nlargest(10, 'pnl').iterrows()))


# pessimistic stop fills on finer bars: stop fills at the bar's extreme (low for longs, high+spread for shorts)
@njit
def replay(o, h, l, c, spr, tod, day, last, ei, dr, N, sl, pess):
    out = np.empty(len(ei)); hitv = np.zeros(len(ei), np.bool_)
    for k in range(len(ei)):
        i = ei[k]; s = dr[k]; e = o[i + 1] + spr[i + 1] if s == 1 else o[i + 1]; b = i + 1
        while True:
            stale = (b - i >= N) or tod[b] >= 22 * 60 + 58 or last[b] or b == len(c) - 1 or day[b] != day[i]
            if s == 1:
                if o[b] <= e - sl: px = o[b]; hitv[k] = True; break
                if l[b] <= e - sl: px = l[b] if pess else e - sl; hitv[k] = True; break
                if stale: px = c[b]; break
            else:
                if o[b] + spr[b] >= e + sl: px = o[b] + spr[b]; hitv[k] = True; break
                if h[b] + spr[b] >= e + sl: px = h[b] + spr[b] if pess else e + sl; hitv[k] = True; break
                if stale: px = c[b] + spr[b]; break
            b += 1
        out[k] = px - e if s == 1 else e - px
    return out, hitv


for tf, B, lo in (('M5', 5, '2025-05-05'), ('M1', 1, '2026-06-26')):
    fd = finish(read(tf)); Ef = Eng(fd, B)
    tt = T[T.entry >= lo]
    pos = fd.index.get_indexer(tt.entry + pd.Timedelta(minutes=15 - B))     # fine bar closing with the signal M15 bar
    ok = pos >= 0
    day_ = fd.index.normalize().values.astype('datetime64[D]').astype(np.int64)
    args = (fd.open.values, fd.high.values, fd.low.values, fd.close.values, fd.spread_usd.values + 0.05, fd.tod.values.astype(np.int64),
            day_, fd.last_of_session.values, pos[ok].astype(np.int64), tt.dir.values[ok].astype(np.int64), int(60 / B), 25.0)
    exact, h1 = replay(*args, False); pess, h2 = replay(*args, True)
    print(f"\n{tf} replay of the pick's M15 trades from {lo} ({int(ok.sum())} of {len(tt)} mapped): M15 sim total {tt.pnl[ok].sum():+.0f}, "
          f"{tf} exact-stop total {exact.sum():+.0f}, {tf} stop-at-bar-extreme total {pess.sum():+.0f}; stops hit {int(h1.sum())}; "
          f"worst trade exact {exact.min():+.1f}, pessimistic {pess.min():+.1f}; mean extra slippage per stop {((exact - pess)[h2]).mean():.2f}")
    if tf == 'M1':
        rng_ = fd.high - fd.low; mv = (fd.close - fd.open).abs()
        big = fd[(rng_ >= 15)]
        print(f"  M1 bars with range >= $15: {len(big)}; >= $20: {int((rng_ >= 20).sum())}; >= $30: {int((rng_ >= 30).sum())}; largest {rng_.max():.1f} at {rng_.idxmax()}")
        for t0 in rng_.nlargest(8).index:
            near = T[(T.entry <= t0) & (T.exit >= t0 - pd.Timedelta(minutes=15))]
            after = T[(T.entry > t0 - pd.Timedelta(minutes=15)) & (T.entry <= t0 + pd.Timedelta(minutes=45))]
            print(f"   {t0} range {rng_[t0]:.1f} body {fd.close[t0] - fd.open[t0]:+.1f}: open trades {len(near)} ({near.pnl.sum():+.1f}), "
                  f"trades signalled within 45 min {len(after)} ({after.pnl.sum():+.1f}, dirs {after.dir.tolist()})")
# M5 big bars (2025-05..): trades overlapping an M5 bar with range >= $25
f5 = finish(read('M5')); r5 = f5.high - f5.low
bigs = r5[r5 >= 25].index
print(f"\nM5 bars with range >= $25 since 2025-05: {len(bigs)} (>= $40: {int((r5 >= 40).sum())}, max {r5.max():.1f} at {r5.idxmax()})")
ov = [((T.entry + pd.Timedelta(minutes=15) <= b) & (T.exit + pd.Timedelta(minutes=15) > b)) for b in bigs]
m = np.any(np.vstack(ov), axis=0) if len(ov) else np.zeros(len(T), bool)
print(f"  pick trades open during such a bar: {int(m.sum())}, total {T.pnl[m].sum():+.0f}, mean {T.pnl[m].mean():+.2f}, stops {int((T.pnl[m] <= -24.5).sum())}, "
      f"worst {T.pnl[m].min():+.1f}; other trades since 2025-05: mean {T.pnl[~m & (T.entry >= '2025-05-05')].mean():+.2f}")
# day bootstrap of one year (250 trading days), TEST days and ALL days
rng = np.random.default_rng(5)
for p, (lo, hi) in (('TRAIN', P['TRAIN']), ('TEST', P['TEST']), ('ALL', P['ALL'])):
    dd = days[(days.index >= lo) & ((days.index < hi) if hi else True)].pnl.values
    tot = []; mdd = []
    for _ in range(4000):
        x = rng.choice(dd, 250); eq = np.cumsum(x); tot.append(eq[-1]); mdd.append((eq - np.maximum.accumulate(eq)).min())
    tot = np.array(tot); mdd = np.array(mdd)
    print(f"bootstrap year from {p} days: P(year < 0) {np.mean(tot < 0):.2f}, median year {np.median(tot):+.0f}, 5th pct {np.quantile(tot, .05):+.0f}, "
          f"median max DD {np.median(mdd):+.0f}, 5th pct max DD {np.quantile(mdd, .05):+.0f} ({100 * np.quantile(mdd, .05) / ACC:.1f}%), P(DD worse than -$300) {np.mean(mdd < -300):.2f}")
