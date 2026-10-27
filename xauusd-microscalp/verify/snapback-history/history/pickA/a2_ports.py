"""Step 2: does pick A hold on other data / other bar alignments?
 P0  M15 file, the pick itself (reference, per window)
 P1  M5 native: AR = mean M5 high-low over 96 bars (8 h), move over 6 M5 bars (30 min), threshold k5 = 4 x (mean M15
     range / mean M5 range), hold 12 M5 bars (60 min), sl 25, max 3, VWAP gate; with and without a 3-bar cooldown
 P2  M5 sliding M15-equivalent: R = 3-bar rolling range, AR = mean R over 96 bars, move over 6 bars, k 4, hold 12
 P3  M15 bars rebuilt from M5 at phase offsets 0 / 5 / 10 min; signal on those bars, executed on M5 bars
     (entry at the next M5 open, exit at the close 60 min after the M15 close, stop checked on M5)
 P4  M1 era: M15 bars rebuilt from M1 at offsets 0..14, executed on M1 bars
 P5  (supplementary, 4x timescale) the same rule on H1 bars 2016-07..2026: n 2, k 4, AR32, gate, hold 4 H1 bars
Every result: base cost (bar spread + $0.05), FAIR fills, next-bar-open entries, EA entry filter;
baselines: 30 random-direction seeds, a direction permutation (same long share) and always-long."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickA')
from alib import *
OUT = '/mnt/project-files/xauusd-microscalp/verify/snapback-history/history/pickA/'
NS = 30
rows = []; qrows = []


def tsel(T, lo, hi):
    m = np.ones(len(T), bool)
    if lo: m &= (T.entry >= pd.Timestamp(lo)).values
    if hi: m &= (T.entry < pd.Timestamp(hi)).values
    return m


def evaluate(name, E, s, N, sl, mo, windows, cooldown=0):
    days, T = E.run(s, N, sl, mo, cooldown=cooldown)
    R = [E.run(rand_dirs(s, z), N, sl, mo, cooldown=cooldown) for z in range(NS)]
    AL = E.run(np.where(s != 0, 1., 0.), N, sl, mo, cooldown=cooldown)
    W = E.run(s, N, sl, mo, spread='wide', cooldown=cooldown)
    # direction permutation: shuffle the pick's directions among its own signal bars (keeps the long share)
    nz = np.where(E.prep(s) != 0)[0]; PM = []
    for z in range(NS):
        sp = np.zeros(len(s)); sp[nz] = np.random.default_rng(100 + z).permutation(np.sign(s[nz])); PM.append(E.run(sp, N, sl, mo, cooldown=cooldown))
    for wn, (lo, hi) in windows.items():
        st = stats(days, T, lo, hi)
        rp = np.array([stats(a, b, lo, hi)['per_day'] for a, b in R]); pp = np.array([stats(a, b, lo, hi)['per_day'] for a, b in PM])
        tt = T[tsel(T, lo, hi)]
        r = dict(port=name, window=wn, **st, wide_per_day=stats(*W, lo, hi)['per_day'],
                 comm_per_day=stats(days, T, lo, hi, extra=COMM)['per_day'], rand_mean=rp.mean(), rand_sd=rp.std(),
                 rand_share_ge=(rp >= st['per_day']).mean(), perm_mean=pp.mean(), perm_share_ge=(pp >= st['per_day']).mean(),
                 always_long=stats(*AL, lo, hi)['per_day'], long_pt=tt.pnl[tt.dir == 1].mean(), short_pt=tt.pnl[tt.dir == -1].mean(),
                 stops=int((tt.pnl <= -sl + 0.5).sum()))
        rows.append(r)
        print(f"{name:28s} {wn:9s} {fmt(st)} | wide {r['wide_per_day']:+.2f} comm {r['comm_per_day']:+.2f} | rand {rp.mean():+.2f} "
              f"(share>= {r['rand_share_ge']:.2f}) perm {pp.mean():+.2f} (share>= {r['perm_share_ge']:.2f}) along {r['always_long']:+.2f} "
              f"| L/tr {r['long_pt']:+.2f} S/tr {r['short_pt']:+.2f} stops {r['stops']}", flush=True)
    q = days.pnl.groupby(days.index.to_period('Q')).mean(); qn = T.groupby(T.entry.dt.to_period('Q')).pnl.agg(['size', 'mean'])
    qr = pd.concat([a.pnl for a, _ in R], axis=1).mean(axis=1).groupby(days.index.to_period('Q')).mean()
    for i in q.index:
        qrows.append(dict(port=name, quarter=str(i), per_day=q[i], trades=int(qn['size'].get(i, 0)), per_trade=qn['mean'].get(i, np.nan), rand=qr[i]))
    print(f"{'':28s} quarters: " + ' '.join(f"{i} {q[i]:+.2f}[{int(qn['size'].get(i, 0))}]" for i in q.index) + f"  positive {int((q > 0).sum())}/{len(q)}")
    return days, T


def on_fine(fine, B, Q, sQ):
    """Map signals computed on rebuilt M15 bars Q to the fine bar that closes with each Q bar."""
    s = np.zeros(len(fine))
    ok = (Q.tod.values >= FIRST) & (Q.tod.values <= LAST)
    last_sub = Q.index + pd.Timedelta(minutes=15 - B)
    pos = fine.index.get_indexer(last_sub)
    m = (sQ != 0) & ok & (pos >= 0)
    s[pos[m]] = sQ[m]
    return s, int(((sQ != 0) & ok & (pos < 0)).sum())


# ---------- M15 reference
d15 = finish(read('M15')); E15 = Eng(d15, 15); s15 = signal(d15, features(d15, 15))
WIN15 = {'TRAIN': ('2022-07-01', '2025-01-01'), 'TEST': ('2025-01-01', None), 'M5WIN': ('2025-05-05', '2026-06-26'),
         'M1ERA': ('2026-06-26', None)}
evaluate('P0 M15 file (the pick)', E15, s15, 4, 25, 3, WIN15)

# ---------- M5
d5r = read('M5'); d5 = finish(d5r); E5 = Eng(d5, 5)
WIN5 = {'M5WIN': ('2025-05-05', '2026-06-26'), 'M1ERA': ('2026-06-26', None), 'ALL5': (None, None)}
Q0 = resample_phase(d5r, 15, 0)
ov = Q0.index.intersection(d15.index[d15.index >= '2025-05-06'])
same = (np.isclose(Q0.loc[ov, ['open', 'high', 'low', 'close']].values, d15.loc[ov, ['open', 'high', 'low', 'close']].values, atol=0.011)).all(axis=1)
print(f'M15 rebuilt from M5 vs M15 file: {len(ov)} common bars, OHLC identical {same.mean():.4f}; '
      f'M15 bars missing in rebuild {len(d15.index[d15.index >= "2025-05-06"].difference(Q0.index))}')
sub = (d5.index >= '2025-05-05') & (d5.index < '2026-06-26')
q15 = Q0[(Q0.index >= '2025-05-05') & (Q0.index < '2026-06-26')]
ratio = (q15.high - q15.low).mean() / (d5.high - d5.low)[sub].mean()
print(f'mean M15 range / mean M5 range (2025-05..2026-06): {ratio:.3f} -> k5 = {4 * ratio:.2f}')
f5n = features(d5, 5, w=1, L=96, n=6)
s_p1 = signal(d5, f5n, 4 * ratio, True)
evaluate('P1 M5 native k5', E5, s_p1, 12, 25, 3, WIN5)
evaluate('P1 M5 native k5 cool3', E5, s_p1, 12, 25, 3, WIN5, cooldown=3)
f5s = features(d5, 5)                       # w = 3: rolling 15-min range, AR over 96 bars, move over 6 bars
s_p2 = signal(d5, f5s, 4.0, True)
evaluate('P2 M5 sliding M15eq', E5, s_p2, 12, 25, 3, WIN5)
evaluate('P2 M5 sliding M15eq cool3', E5, s_p2, 12, 25, 3, WIN5, cooldown=3)
for off in (0, 5, 10):
    Q = finish(resample_phase(d5r, 15, off)); sQ = signal(Q, features(Q, 15))
    s_f, miss = on_fine(d5, 5, Q, sQ)
    evaluate(f'P3 M15@+{off} on M5', E5, s_f, 12, 25, 3, WIN5)
    if off == 0:
        evaluate('P3 M15@+0 on rebuilt M15', Eng(Q, 15), sQ, 4, 25, 3, WIN5)

# ---------- M1 era
d1r = read('M1'); d1 = finish(d1r); E1 = Eng(d1, 1)
WIN1 = {'M1ERA': (None, None), 'M1_TRAIN': (None, '2026-09-01'), 'M1_TEST': ('2026-09-01', None)}
acc = []
for off in range(15):
    Q = finish(resample_phase(d1r, 15, off)); sQ = signal(Q, features(Q, 15))
    s_f, miss = on_fine(d1, 1, Q, sQ)
    dd, TT = evaluate(f'P4 M15@+{off} on M1', E1, s_f, 60, 25, 3, WIN1) if off in (0, 5, 10) else E1.run(s_f, 60, 25, 3)
    st = stats(dd, TT); acc.append((off, st['per_day'], st['trades'], st['per_trade']))
print('P4 all 15 phases on M1 (M1 era $/day [trades]): ' + ' '.join(f'+{o}:{p:+.2f}[{n}]' for o, p, n, _ in acc)
      + f' | mean {np.mean([a[1] for a in acc]):+.2f}, positive {sum(a[1] > 0 for a in acc)}/15')
rows.append(dict(port='P4 all 15 phases', window='M1ERA', per_day=np.mean([a[1] for a in acc]), trades=int(np.mean([a[2] for a in acc]))))

# ---------- H1 (supplementary)
dh = finish(read('H1'), 60); Eh = Eng(dh, 60); sh = signal(dh, features(dh, 60, w=1))
WINH = {'H1_2016_22': ('2016-07-01', '2022-07-01'), 'H1_2022_24': ('2022-07-01', '2025-01-01'), 'H1_2025_26': ('2025-01-01', None)}
evaluate('P5 H1 hold4 sl25', Eh, sh, 4, 25, 3, WINH)
evaluate('P5 H1 hold4 sl50', Eh, sh, 4, 50, 3, WINH)
pd.DataFrame(rows).to_csv(OUT + 'ports_summary.csv', index=False)
pd.DataFrame(qrows).to_csv(OUT + 'ports_quarters.csv', index=False)
