"""(1) P2 ported to M5 (2025-05-05..2026-06-25, before the M1 file) and M15 (2022-07..2026), plus the M1 period as a
bridge. Port fixed BEFORE running (h1_calibrate.out gives the scale factors; no P&L was looked at to set them):
  move     : 1-bar close change (3 minutes -> nearest whole bar = 1 bar on M5 and on M15)
  ATR      : mean(High-Low) over 240 minutes of bars = 48 M5 / 16 M15 bars, incl. bar i
  threshold: M5 primary k = 1.05 (same ~$5.1 move as 2.5 x ATR240(M1) on the overlap period: ATR_M1/ATR_M5 = 0.421),
             M5 secondary k = 1.35 (same z-size of move); M15 primary k = 1.30 (same z-size), secondary 0.59 (same $);
             grid k 1.0/1.5/2.0/2.5 reported for transparency, nothing is selected from it
  gate     : toward-VWAP (session VWAP from 01:00, typical price x tick volume); direction = sign(Close - VWAP)
  spread   : signal-bar recorded spread <= 15 pts, next-bar recorded spread <= 50 pts (both nearly always pass on
             M5/M15 because the recorded value is the bar minimum)
  hold     : 15 minutes -> 3 M5 bars / 1 M15 bar (exit at the close), $25 disaster stop, max 3 open, no cooldown,
             entry at the next bar open if it follows directly (gap = bar length), signal bar 01:05-22:29
  costs    : flat $0.20 per trade (P2 paid $0.175 TRAIN / $0.200 TEST on M1 with the base model), flat $0.30,
             $0.20 + $0.07 commission, gross (cost 0) to see the raw move
Baselines on the same bars: random directions (40 seeds primary, 20 grid), always long, always short; and a
'VWAP side only' baseline: random bars (same count per period) traded in the direction sign(Close - VWAP)."""
import sys, json; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *

PER = {'M5': [('pre-M1 2025-05-05..2026-06-25', '2025-05-05', '2026-06-26'),
              ('M1 period, M1-TRAIN dates', '2026-06-26', '2026-09-01'), ('M1 period, M1-TEST dates', '2026-09-01', '2026-10-10')],
       'M15': [('2022-07..2025-05-04', '2022-07-01', '2025-05-05'), ('2025-05-05..2026-06-25', '2025-05-05', '2026-06-26'),
               ('M1 period, M1-TRAIN dates', '2026-06-26', '2026-09-01'), ('M1 period, M1-TEST dates', '2026-09-01', '2026-10-10')]}
CFG = {'M5': dict(natr=48, hold=3, primary=[1.05, 1.35], grid=[1.0, 1.5, 2.0, 2.5]),
       'M15': dict(natr=16, hold=1, primary=[1.30, 0.59], grid=[1.0, 1.5, 2.0, 2.5])}
NS_P, NS_G = 40, 20
rows, qrows = [], []
ncfg = 0
for tf in ('M5', 'M15'):
    m = load_tf(tf); A = Arr(m, tf); C = CFG[tf]
    F = A.feats(1, C['natr']); side = np.sign(A.c - F['vw'])
    elig = A.ea_filter(np.ones(len(m))) != 0
    elig &= (A.tod >= 65) & (A.tod <= 1349) & ~np.isnan(side) & (side != 0)
    print(f'\n===== {tf}: {m.index[0]} .. {m.index[-1]}')
    for k in C['primary'] + C['grid']:
        prim = k in C['primary']
        s = A.signal(k=k, L=1, atr_n=C['natr'])
        run = lambda sig, spr=0.20, **kw: A.run(sig, sl=25.0, hold=C['hold'], mo=3, spr=spr, **kw)
        d, t = run(s); dg, tg = run(s, spr=0.0); dw, tw = run(s, spr=0.30)
        ns = NS_P if prim else NS_G
        R = [run(random_like(s, z)) for z in range(ns)]
        dl, tl = run(np.where(s != 0, 1.0, 0.0)); dsh, tsh = run(np.where(s != 0, -1.0, 0.0))
        ncfg += 5 + ns
        # VWAP-side-only baseline: random eligible bars, same count of signal bars per period, direction = side
        VB = []
        for z in range(10 if prim else 0):
            rng = np.random.default_rng(1000 + z); sb = np.zeros(len(m))
            for nm, a, b in PER[tf]:
                sel = np.flatnonzero(elig & (m.index >= a) & (m.index < b)); cnt = int(((s != 0) & (m.index >= a) & (m.index < b)).sum())
                if cnt and len(sel): sb[rng.choice(sel, min(cnt, len(sel)), replace=False)] = 1
            VB.append(run(np.where(sb != 0, side, 0.0)))
        ncfg += len(VB)
        for nm, a, b in PER[tf]:
            a, b = pd.Timestamp(a), pd.Timestamp(b)
            r = summ(d, t, a, b); g = summ(dg, tg, a, b); w = summ(dw, tw, a, b); cm = summ(d, t, a, b, fee=0.07)
            rr = np.array([summ(*x, a, b)['per_day'] for x in R])
            vb = np.array([summ(*x, a, b)["per_day"] for x in VB]) if VB else np.array([np.nan, np.nan])
            row = dict(tf=tf, k=k, primary=prim, period=nm, per_day=r['per_day'], trades_day=r['trades_day'], per_trade=r['per_trade'],
                       gross_per_trade=g['per_trade'], win=r['win'], wide_per_day=w['per_day'], comm_per_day=cm['per_day'],
                       worst_day=r['worst_day'], worst_trade=r['worst_trade'], max_dd=r['max_dd'], long_share=r['long_share'],
                       days=r['days'], n=r['n'], rand_mean=rr.mean(), rand_sd=rr.std(), share_rand_ge=(rr >= r['per_day']).mean(),
                       long_per_day=summ(dl, tl, a, b)['per_day'], short_per_day=summ(dsh, tsh, a, b)['per_day'],
                       vwapside_per_day=(np.nanmean(vb) if VB else np.nan), stops=int((t[(t.entry >= a) & (t.entry < b)].pnl <= -24.99).sum()))
            rows.append(row)
            if prim:
                print(f'{tf} k {k:.2f} {nm:32s} {r["per_day"]:+6.2f}/day {r["trades_day"]:4.1f} tr/d {r["per_trade"]:+.3f}/tr gross {g["per_trade"]:+.3f}/tr '
                      f'win {r["win"]:.2f} | $0.30 {w["per_day"]:+6.2f} | +comm {cm["per_day"]:+6.2f} | worstD {r["worst_day"]:+6.1f} DD {r["max_dd"]:+7.1f} '
                      f'long {r["long_share"]:.2f} | random {rr.mean():+.2f} (sd {rr.std():.2f}, share>=pick {(rr >= r["per_day"]).mean():.2f}) '
                      f'long {row["long_per_day"]:+.2f} short {row["short_per_day"]:+.2f} vwap-side {np.nanmean(vb):+.2f}')
        if prim:
            q = d.index.to_period('Q'); tq = t.entry.dt.to_period('Q'); tgq = tg.entry.dt.to_period('Q')
            rq = pd.concat([x[0].pnl for x in R], axis=1).mean(axis=1).groupby(q).mean()
            for qq in sorted(q.unique()):
                tt = t[tq == qq]; dd = d[q == qq]
                qrows.append(dict(tf=tf, k=k, quarter=str(qq), days=len(dd), per_day=dd.pnl.mean(), trades_day=len(tt) / max(len(dd), 1),
                                  per_trade=tt.pnl.mean() if len(tt) else np.nan, gross_per_trade=tg[tgq == qq].pnl.mean() if len(tt) else np.nan,
                                  rand_per_day=rq.get(qq, np.nan), worst_day=dd.pnl.min()))
R = pd.DataFrame(rows); Q = pd.DataFrame(qrows)
R.to_csv(OUT + 'h2_ports.csv', index=False); Q.to_csv(OUT + 'h2_ports_quarters.csv', index=False)
print('\nquarter by quarter, primary ports ($0.20/trade): $/day [gross $/trade] (random-direction $/day)')
for (tf, k), g in Q.groupby(['tf', 'k']):
    print(f'{tf} k {k:.2f}: ' + '  '.join(f'{r.quarter} {r.per_day:+.2f} [{r.gross_per_trade:+.2f}] ({r.rand_per_day:+.2f})' for r in g.itertuples()))
    pre = g[g.quarter < '2026Q2']
    print(f'   quarters before the M1 file with $/day > 0: {(pre.per_day > 0).sum()} of {len(pre)}; gross $/trade > 0: {(pre.gross_per_trade > 0).sum()} of {len(pre)}')
print('\ngrid (k not used for any decision), $/day at $0.20 [gross $/trade]:')
for (tf, k), g in R[~R.primary].groupby(['tf', 'k']):
    print(f'{tf} k {k:.1f}: ' + ' | '.join(f'{r.period[:22]} {r.per_day:+.2f} [{r.gross_per_trade:+.2f}] rnd {r.rand_mean:+.2f}' for r in g.itertuples()))
print('\nconfigurations simulated in this script (incl. baselines):', ncfg)
