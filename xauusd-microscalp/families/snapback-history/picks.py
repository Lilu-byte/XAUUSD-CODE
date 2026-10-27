"""Full report for the three pre-specified picks (rule in summarize.py). 'test' = the data after each TF's SEL period."""
import sys, json; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-history')
from hlib import *
OUT = '/mnt/project-files/xauusd-microscalp/families/snapback-history/'
PER = {'M5': {'SEL': ('2025-05-05', '2026-01-01'), 'TEST': ('2026-01-01', None),
              'TEST_CLEAN': ('2026-01-01', '2026-06-26'), 'M1ERA': ('2026-06-26', None), 'PRE_M1': ('2025-05-05', '2026-06-26')},
       'M15': {'SEL': ('2022-07-01', '2025-01-01'), 'TEST': ('2025-01-01', None),
               'TEST_CLEAN': ('2025-01-01', '2026-06-26'), 'M1ERA': ('2026-06-26', None), 'PRE_M1': ('2022-07-01', '2026-06-26')}}
PICKS = [('A_M15_n2_k4_vwap_N4_sl25_mo3', 'M15', 2, 4.0, 1, 4, 25, 3),
         ('B_M5_n1_k4_nogate_N6_sl10_mo1', 'M5', 1, 4.0, 0, 6, 10, 1),
         ('C_M15_n2_k4_vwap_N2_sl25_mo3', 'M15', 2, 4.0, 1, 2, 25, 3)]
res = {}
cache = {}
for name, tf, n, k, g, N, sl, mo in PICKS:
    if tf not in cache:
        d = load_tf(tf); f = features(d, tf); cache[tf] = (d, f, Scorer(d, tf, f.ar))
    d, f, S = cache[tf]
    s = signal(d, f, n, k, g)
    runs = {'base': S.run(s, N, sl, mo), 'bar': S.run(s, N, sl, mo, spread='bar'), 'wide': S.run(s, N, sl, mo, spread='wide'),
            'ohlc': S.run(s, N, sl, mo, fill='OHLC'), 'stop': S.run(s, N, sl, mo, fill='STOP'),
            'lat1': S.run(s, N, sl, mo, latency=1),
            'along': S.run(np.where(s != 0, 1., 0.), N, sl, mo), 'ashort': S.run(np.where(s != 0, -1., 0.), N, sl, mo)}
    rnd = [S.run(random_like(s, z), N, sl, mo) for z in range(20)]
    out = {}
    for pn, (lo, hi) in PER[tf].items():
        st = stats(*runs['base'], lo, hi)
        st.update({f'{v}_per_day': stats(*runs[v], lo, hi)['per_day'] for v in ('bar', 'wide', 'ohlc', 'stop', 'lat1', 'along', 'ashort')})
        st['comm_per_day'] = stats(*runs['base'], lo, hi, extra=COMMISSION)['per_day']
        rp = np.array([stats(a, b, lo, hi)['per_day'] for a, b in rnd])
        st['rand_per_day'] = rp.mean(); st['rand_max'] = rp.max(); st['rand_beat_share'] = (rp >= st['per_day']).mean()
        T = runs['base'][1]; sel = np.ones(len(T), bool)
        if lo: sel &= T.entry >= pd.Timestamp(lo)
        if hi: sel &= T.entry < pd.Timestamp(hi)
        t = T[sel]
        st['long_pt'] = t.pnl[t.dir == 1].mean(); st['short_pt'] = t.pnl[t.dir == -1].mean()
        st['stops_hit'] = int((t.pnl <= -sl + 0.5).sum()); st['pt_over_ar'] = (t.pnl / t.ar).mean()
        out[pn] = st
    days, T = runs['base']
    q = days.pnl.groupby(days.index.to_period('Q').astype(str)).mean()
    qt = T.groupby(T.entry.dt.to_period('Q').astype(str)).pnl.agg(['size', 'mean'])
    qw = runs['wide'][0].pnl.groupby(runs['wide'][0].index.to_period('Q').astype(str)).mean()
    qr = pd.concat([a.pnl for a, _ in rnd], axis=1).mean(axis=1).groupby(days.index.to_period('Q').astype(str)).mean()
    y = days.pnl.groupby(days.index.year).mean(); yt = T.groupby(T.entry.dt.year).pnl.agg(['size', 'mean'])
    yw = runs['wide'][0].pnl.groupby(runs['wide'][0].index.year).mean()
    yr_ = pd.concat([a.pnl for a, _ in rnd], axis=1).mean(axis=1).groupby(days.index.year).mean()
    hist = 'quarters $/day base (wide $0.30) [trades, $/trade] random: ' + '; '.join(
        f"{i} {q[i]:+.2f} ({qw[i]:+.2f}) [{int(qt['size'].get(i, 0))}, {qt['mean'].get(i, np.nan):+.2f}] r{qr[i]:+.2f}" for i in q.index)
    hist += ' || years: ' + '; '.join(f"{i} {y[i]:+.2f} ({yw[i]:+.2f}) [{int(yt['size'].get(i, 0))}, {yt['mean'].get(i, np.nan):+.2f}] r{yr_[i]:+.2f}" for i in y.index)
    hist += ' || subperiods $/day: ' + '; '.join(f"{p} {out[p]['per_day']:+.2f} ({out[p]['trades_day']:.2f} tr/d, {out[p]['per_trade']:+.2f}/tr, random {out[p]['rand_per_day']:+.2f})" for p in ('TEST_CLEAN', 'M1ERA', 'PRE_M1'))
    res[name] = dict(tf=tf, n=n, k=k, gate=g, N=N, sl=sl, max_open=mo, periods=out, history=hist,
                     pos_quarters=f"{int((q > 0).sum())}/{len(q)}")
    print(f'\n##### {name}  positive quarters {(q > 0).sum()}/{len(q)}')
    for pn, st in out.items():
        print(f"  {pn:10s} {st['per_day']:+.2f}/d  {st['trades_day']:.2f} tr/d  win {st['win']:.2f}  {st['per_trade']:+.3f}/tr  "
              f"days>=5 {st['days_ge5']:.2f} losing {st['losing_days']:.2f} worst day {st['worst_day']:+.1f} worst tr {st['worst_trade']:+.1f} "
              f"maxDD {st['max_dd']:+.1f} | bar {st['bar_per_day']:+.2f} wide {st['wide_per_day']:+.2f} comm {st['comm_per_day']:+.2f} "
              f"ohlc {st['ohlc_per_day']:+.2f} stop {st['stop_per_day']:+.2f} lat1 {st['lat1_per_day']:+.2f} | rand {st['rand_per_day']:+.2f} "
              f"(max {st['rand_max']:+.2f}, beat {st['rand_beat_share']:.2f}) along {st['along_per_day']:+.2f} ashort {st['ashort_per_day']:+.2f} "
              f"| long share {st['long_share']:.2f} long/tr {st['long_pt']:+.2f} short/tr {st['short_pt']:+.2f} stops {st['stops_hit']} pt/AR {st['pt_over_ar']:+.3f}")
    print('  ' + hist)
json.dump(res, open(OUT + 'picks.json', 'w'), indent=1, default=float)
