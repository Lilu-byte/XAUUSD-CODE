"""Every pre-specified setting, scored with ea_sim._sim_next (next-bar-open entry, EA entry rules), FAIR fills,
base spread (recorded bar spread + $0.05), pure time exit (TP 1000) with a disaster stop.
Grid: TF M5 {n 1,2} x {k 2.5,3,4} x {gate 0,1} x {N 1,2,3,6} x {sl 10,25} x {max_open 1,3}  = 192
      TF M15 same but N {1,2,4}                                                             = 144
Writes grid_summary.csv (one row per setting x period) and grid_quarters.csv (per calendar quarter).
Baselines per setting: 20 random-direction seeds, always-long and always-short on the same signal bars."""
import sys, time; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-history')
from hlib import *
OUT = '/mnt/project-files/xauusd-microscalp/families/snapback-history/'
PER = {'M5': {'SEL': ('2025-05-05', '2026-01-01'), 'LATER': ('2026-01-01', None),
              'LATER_CLEAN': ('2026-01-01', '2026-06-26'), 'M1ERA': ('2026-06-26', None),
              'PRE_M1': ('2025-05-05', '2026-06-26'), 'ALL': (None, None)},
       'M15': {'SEL': ('2022-07-01', '2025-01-01'), 'LATER': ('2025-01-01', None),
               'LATER_CLEAN': ('2025-01-01', '2026-06-26'), 'M1ERA': ('2026-06-26', None),
               'PRE_M1': ('2022-07-01', '2026-06-26'), 'ALL': (None, None)}}
NS = {'M5': (1, 2, 3, 6), 'M15': (1, 2, 4)}
NSEED = 20
t0 = time.time()
rows = []; qrows = []; nconf = 0; nsims = 0
for tf in ('M5', 'M15'):
    d = load_tf(tf); f = features(d, tf); S = Scorer(d, tf, f.ar)
    qkeys = d.index.to_period('Q').astype(str)
    for n in (1, 2):
        for k in (2.5, 3, 4):
            for g in (0, 1):
                s = signal(d, f, n, k, g)
                rnd = [random_like(s, z) for z in range(NSEED)]
                al = np.where(s != 0, 1.0, 0.0); ash = -al
                for N in NS[tf]:
                    for sl in (10, 25):
                        for mo in (1, 3):
                            nconf += 1
                            key = dict(tf=tf, n=n, k=k, gate=g, N=N, sl=sl, max_open=mo)
                            days, T = S.run(s, N, sl, mo)
                            dB, TB = S.run(s, N, sl, mo, spread='bar')
                            dW, TW = S.run(s, N, sl, mo, spread='wide')
                            dL, TL = S.run(s, N, sl, mo, latency=1)
                            dAL, TAL = S.run(al, N, sl, mo); dAS, TAS = S.run(ash, N, sl, mo)
                            RR = [S.run(r, N, sl, mo) for r in rnd]
                            nsims += 6 + NSEED
                            for pn, (lo, hi) in PER[tf].items():
                                st = stats(days, T, lo, hi)
                                r = dict(key, period=pn, **st)
                                r['bar_per_day'] = stats(dB, TB, lo, hi)['per_day']
                                r['wide_per_day'] = stats(dW, TW, lo, hi)['per_day']
                                r['comm_per_day'] = stats(days, T, lo, hi, extra=COMMISSION)['per_day']
                                r['lat1_per_day'] = stats(dL, TL, lo, hi)['per_day']
                                r['long_per_day'] = stats(dAL, TAL, lo, hi)['per_day']
                                r['short_per_day'] = stats(dAS, TAS, lo, hi)['per_day']
                                rp = np.array([stats(a, b, lo, hi)['per_day'] for a, b in RR])
                                r['rand_per_day'] = rp.mean(); r['rand_sd'] = rp.std(); r['rand_beats'] = (rp >= st['per_day']).mean()
                                sel = (T.entry >= pd.Timestamp(lo)) if lo else np.ones(len(T), bool)
                                if hi: sel = sel & (T.entry < pd.Timestamp(hi))
                                tt = T[sel]
                                r['long_pt'] = tt.pnl[tt.dir == 1].mean(); r['short_pt'] = tt.pnl[tt.dir == -1].mean()
                                r['n_long'] = (tt.dir == 1).sum(); r['n_short'] = (tt.dir == -1).sum()
                                r['per_trade_over_ar'] = (tt.pnl / tt.ar).mean()
                                rows.append(r)
                            # per quarter
                            dq = days.groupby(days.index.to_period('Q').astype(str))
                            tq = T.groupby(T.entry.dt.to_period('Q').astype(str))
                            rq = pd.concat([a.pnl for a, _ in RR], axis=1).mean(axis=1).groupby(days.index.to_period('Q').astype(str)).mean()
                            alq = dAL.pnl.groupby(dAL.index.to_period('Q').astype(str)).mean()
                            asq = dAS.pnl.groupby(dAS.index.to_period('Q').astype(str)).mean()
                            wq = dW.pnl.groupby(dW.index.to_period('Q').astype(str)).mean()
                            for q, gq in dq:
                                tqq = tq.get_group(q) if q in tq.groups else T.iloc[:0]
                                qrows.append(dict(key, quarter=q, days=len(gq), per_day=gq.pnl.mean(), trades=len(tqq),
                                                  per_trade=tqq.pnl.mean() if len(tqq) else np.nan,
                                                  win=(tqq.pnl > 0).mean() if len(tqq) else np.nan,
                                                  worst_day=gq.pnl.min(), wide_per_day=wq.get(q, np.nan),
                                                  rand_per_day=rq.get(q, np.nan), long_per_day=alq.get(q, np.nan),
                                                  short_per_day=asq.get(q, np.nan),
                                                  long_share=(tqq.dir == 1).mean() if len(tqq) else np.nan))
    print(tf, 'done', round(time.time() - t0), 's', flush=True)
G = pd.DataFrame(rows); Q = pd.DataFrame(qrows)
G.to_csv(OUT + 'grid_summary.csv', index=False); Q.to_csv(OUT + 'grid_quarters.csv', index=False)
print(f'configurations scored: {nconf} settings; simulations run (incl. cost/latency variants and baselines): {nsims}')
