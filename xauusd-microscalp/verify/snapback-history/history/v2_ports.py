"""Step 2: port pick C to other bar data. Rule fixed (k = 4, VWAP gate, 30-min move, 8-hour average range,
30-min hold, $25 stop, up to 3 open). No parameter is tuned here. Writes ports_quarters.csv, ports_summary.csv."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history')
from vlib import *
OUT = '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/'
NSEED = 50
rows = []; qrows = []


def score(name, d, B, s, N, lo, hi, cooldown=0, spread='base', sl=25, mo=3, eng=None, periods=None):
    E = eng or Eng(d, B)
    days, T = E.run(s, N, sl, mo, spread=spread, cooldown=cooldown)
    dW, TW = E.run(s, N, sl, mo, spread='wide', cooldown=cooldown)
    idx = np.where(s != 0)[0]; rng = np.random.default_rng(3)
    RR = []
    for z in range(NSEED):
        r = np.zeros(len(s)); r[idx] = np.where(rng.random(len(idx)) < .5, 1, -1)
        RR.append(E.run(r, N, sl, mo, spread=spread, cooldown=cooldown)[0].pnl)
    RR = pd.concat(RR, axis=1)
    dl, _ = E.run(np.where(s != 0, 1., 0.), N, sl, mo, spread=spread, cooldown=cooldown)
    dsh, _ = E.run(np.where(s != 0, -1., 0.), N, sl, mo, spread=spread, cooldown=cooldown)
    periods = periods or {'MAIN': (lo, hi)}
    for pn, (a, b) in periods.items():
        st = stats(days, T, a, b)
        sel = np.ones(len(days), bool)
        if a: sel &= days.index >= pd.Timestamp(a)
        if b: sel &= days.index < pd.Timestamp(b)
        rp = RR[sel].mean(axis=0).values
        st.update(name=name, period=pn, wide=dW.pnl[sel].mean(), comm=stats(days, T, a, b, extra=COMM)['per_day'],
                  rand=rp.mean(), rand_share_ge=(rp >= st['per_day']).mean(), along=dl.pnl[sel].mean(), ashort=dsh.pnl[sel].mean())
        rows.append(st)
        print(f"{name:34s} {pn:9s} {fmt(st)} | flat.30 {st['wide']:+.3f} comm {st['comm']:+.3f} | rand {st['rand']:+.3f} "
              f"share>= {st['rand_share_ge']:.2f} | AL {st['along']:+.3f} AS {st['ashort']:+.3f}", flush=True)
    sel = np.ones(len(days), bool)
    if lo: sel &= days.index >= pd.Timestamp(lo)
    if hi: sel &= days.index < pd.Timestamp(hi)
    dd = days[sel]; q = dd.index.to_period('Q').astype(str)
    tq = T[(T.entry >= pd.Timestamp(lo)) if lo else np.ones(len(T), bool)]
    if hi: tq = tq[tq.entry < pd.Timestamp(hi)]
    tqk = tq.entry.dt.to_period('Q').astype(str)
    rq = RR[sel].mean(axis=1)
    for k_ in sorted(set(q)):
        m = q == k_; tt = tq[tqk == k_]
        qrows.append(dict(name=name, quarter=k_, days=int(m.sum()), per_day=dd.pnl[m].mean(), wide=dW.pnl[sel][m].mean(),
                          trades=len(tt), per_trade=tt.pnl.mean() if len(tt) else np.nan, rand=rq[m].mean()))
    qq = [r for r in qrows if r['name'] == name]
    print('   quarters: ' + ' '.join(f"{r['quarter']} {r['per_day']:+.2f}[{r['trades']}]r{r['rand']:+.2f}" for r in qq)
          + f"  -> positive {sum(r['per_day'] > 0 for r in qq)}/{len(qq)}", flush=True)
    return days, T


# --- P1: M15 file, the pick itself
d15 = load('M15'); f, w = features(d15, 15); s = signal(d15, f, 2, 4.0, 1)
score('P1 M15 file (pick C)', d15, 15, s, 2, '2022-07-01', None,
      periods={'2022H2-24': ('2022-07-01', '2025-01-01'), '2025-26Jun': ('2025-01-01', '2026-06-26'), 'M1ERA': ('2026-06-26', None)})

# --- P2: M5 sliding (M15-equivalent range from 3 M5 bars, every 5-min offset)
d5 = load('M5'); E5 = Eng(d5, 5)
f5, w5 = features(d5, 5); s5 = signal(d5, f5, 6, 4.0, 1)
PER5 = {'PRE_M1': ('2025-05-05', '2026-06-26'), 'M1ERA': ('2026-06-26', None)}
score('P2 M5 sliding mo3', d5, 5, s5, 6, '2025-05-05', '2026-06-26', eng=E5, periods=PER5)
score('P2b M5 sliding mo3 cooldown 3 bars', d5, 5, s5, 6, '2025-05-05', '2026-06-26', cooldown=3, eng=E5, periods=PER5)
score('P2c M5 sliding mo1', d5, 5, s5, 6, '2025-05-05', '2026-06-26', mo=1, eng=E5, periods=PER5)
# --- P3: M5 own range: AR = mean(H-L) of 96 M5 bars, k scaled by mean(3-bar range)/mean(1-bar range) on 2025-05..2025-12
sel = (d5.index < '2026-01-01')
r1 = (d5.high - d5.low)[sel].mean(); r3 = (d5.high.rolling(3).max() - d5.low.rolling(3).min())[sel].mean()
kk = 4.0 * r3 / r1
print(f'P3 scale: mean 3-bar range {r3:.3f} / 1-bar range {r1:.3f} -> k = {kk:.2f}')
f5o, _ = features(d5, 5, w=1, L=96); s5o = signal(d5, f5o, 6, kk, 1)
score('P3 M5 own range k=4*ratio', d5, 5, s5o, 6, '2025-05-05', '2026-06-26', eng=E5, periods=PER5)
# --- P4: M15 bars built from M5 at window offsets 0/5/10 minutes
for off in (0, 5, 10):
    dq = resample_offset(d5, off); fq, _ = features(dq, 15); sq = signal(dq, fq, 2, 4.0, 1)
    if off == 0:
        j = dq.index.intersection(d15.index)
        same = (np.sign(sq[dq.index.get_indexer(j)]) == np.sign(s[d15.index.get_indexer(j)])).mean()
        print(f'P4 offset 0 vs M15 file: {len(j)} common bars, signal agreement {same:.4f}')
    score(f'P4 M15-from-M5 offset {off:02d}', dq, 15, sq, 2, '2025-05-05', '2026-06-26', periods=PER5)
# --- P5: M1 sliding (M1 era only, realistic M1 spreads) and M15-from-M1 at the 15 offsets
d1 = load('M1'); E1 = Eng(d1, 1)
f1, _ = features(d1, 1); s1 = signal(d1, f1, 30, 4.0, 1)
score('P5 M1 sliding mo3', d1, 1, s1, 30, None, None, eng=E1)
score('P5b M1 sliding mo3 cooldown 15', d1, 1, s1, 30, None, None, cooldown=15, eng=E1)
# --- P6: H1 (independent years 2016-07..2022-06). (a) nearest whole bar: n=1, AR over 8 H1 bars, hold 1 bar
#         (b) same bar counts as M15: n=2, AR over 32 H1 bars, hold 2 bars
raw = pd.read_csv('/mnt/project-files/xauusd-price-action/data/XAUUSD_H1.csv')
raw.index = pd.to_datetime(raw.time, format='%Y.%m.%d %H:%M')
raw = raw[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].astype(float); raw = raw[raw.index.dayofweek < 5]
dh = finish(raw, 60); EH = Eng(dh, 60)
print('H1 bars', len(dh), 'last-of-session share', round(dh.last_of_session.mean(), 3), 'signals a', int((signal(dh, features(dh, 60, w=1, L=8)[0], 1, 4.0, 1) != 0).sum()))
PERH = {'2016H2-22H1': ('2016-07-01', '2022-07-01'), '2022H2-24': ('2022-07-01', '2025-01-01'), '2025-26': ('2025-01-01', None)}
fa, _ = features(dh, 60, w=1, L=8); sa = signal(dh, fa, 1, 4.0, 1)
score('P6a H1 nearest bar n1 L8 N1', dh, 60, sa, 1, '2016-07-01', '2022-07-01', eng=EH, periods=PERH)
fb, _ = features(dh, 60, w=1, L=32); sb = signal(dh, fb, 2, 4.0, 1)
score('P6b H1 same bar counts n2 L32 N2', dh, 60, sb, 2, '2016-07-01', '2022-07-01', eng=EH, periods=PERH)
pd.DataFrame(rows).to_csv(OUT + 'ports_summary.csv', index=False); pd.DataFrame(qrows).to_csv(OUT + 'ports_quarters.csv', index=False)
print('configurations scored in this step (rule variants x data sets, excluding baselines/cost variants): 11')
