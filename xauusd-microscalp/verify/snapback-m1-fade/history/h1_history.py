"""Lens (1): port P1 to M5 (2025-05-05..2026-06-25, before the M1 file) and M15 (2022-07..2026-06-25), plus the M1 period
as a calibration check. PRE-REGISTERED (fixed before any history outcome was looked at):

P1 on M1: fade |Close[i]-Close[i-3]| > $7, entry next-bar open, pure time exit after 3 bars, max 2 open, $10 stop.
On the M1 period P1 fires on q = 2.16% of M1 bars in entry hours; $7 = 3.4 x mean M1 range; $10 = 4.87 x mean M1 range;
average cost paid per P1 trade (base model) = $0.199.

Ports (ATR = mean high-low of the last 240 bars of the port's own timeframe, causal):
  A  'same clock'   : 1-bar move (5 / 15 min ~ 3 min), hold 1 bar, threshold K so the signal fires on q of bars
  B  'same bars'    : 3-bar move, hold 3 bars, threshold K percentile-matched to q
  L  'literal'      : 3-bar move > 3.4 x ATR, hold 3 bars (P1's $7 in units of its own bar's mean range)
  C  'still running': as A, and the bar closes in the outer 20% of its range in the move's direction
  K for A/B/C is the (1-q) quantile of |move|/ATR on the port's bars inside the M1 period (frequency only; no
  outcomes used). Sensitivity: A and B also at q/2 and 2q.
  All: max 2 open, entry at the next bar open only if that bar follows directly, time exit at the close of the
  last held bar, disaster stop 4.87 x ATR (median ATR of the PREVIOUS calendar quarter, so it is causal), FAIR fills,
  every position closed at session end (mlib v2 rules). No spread filter (recorded M5/M15 spread is the bar minimum;
  on M1 the $0.50 filter removed 2 of 2,107 P1 signals).
Costs per trade: gross (0), flat $0.20 (= P1's average), flat $0.30, and 'vol-scaled' $0.20 x ATR(prev quarter) /
ATR(M1 period) (generous: assumes the spread shrinks with volatility, which it does not do fully).
Baselines: 20 random-direction seeds on the same bars, always long, always short (at $0.20).
"""
import sys, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history')
from vlib import *

Q_P1 = 0.0216
K_LIT = 3.4
SL_ATR = 4.87
COST = 0.20
ATR_N = 240
PERIODS = {'M5': [('M5 2025-05-05..2026-06-25 (pre-M1)', pd.Timestamp('2025-05-01'), M1START),
                  ('M5 on the M1 period', M1START, pd.Timestamp('2026-10-10'))],
           'M15': [('M15 2022-07..2025-05-04', pd.Timestamp('2022-07-01'), pd.Timestamp('2025-05-05')),
                   ('M15 2025-05-05..2026-06-25', pd.Timestamp('2025-05-05'), M1START),
                   ('M15 on the M1 period', M1START, pd.Timestamp('2026-10-10'))]}
NCFG = 0


def feats(x):
    f = pd.DataFrame(index=x.index)
    f['atr'] = (x.high - x.low).rolling(ATR_N).mean()
    for k in (1, 3):
        f[f'r{k}'] = x.close - x.close.shift(k)
    rng = (x.high - x.low).replace(0, np.nan)
    f['pos'] = (x.close - x.low) / rng                     # 0 = close at low, 1 = close at high
    f['okh'] = (x.tod >= 65) & (x.tod <= 22 * 60 + 29) & ~x.last_of_session
    return f


def calib_K(f, k, q, extreme=False):
    sel = (f.index >= M1START) & f.okh.values & f.atr.notna().values
    z = (f[f'r{k}'].abs() / f.atr)[sel]
    if extreme:
        r = f[f'r{k}'][sel]; p = f.pos[sel]
        ok = ((r > 0) & (p >= 0.8)) | ((r < 0) & (p <= 0.2))
        # same overall signal rate q: quantile taken over all bars, counting only 'still running' bars as candidates
        zz = np.where(ok, z, 0.0)
        return float(np.quantile(zz, 1 - q))
    return float(np.quantile(z.dropna(), 1 - q))


def signal(f, k, K, extreme=False):
    r = f[f'r{k}'].values; a = f.atr.values
    hit = np.abs(r) > K * a
    hit &= ~np.isnan(a)
    if extreme:
        p = f.pos.values
        hit &= ((r > 0) & (p >= 0.8)) | ((r < 0) & (p <= 0.2))
    return np.where(hit, -np.sign(r), 0.0)


def run_q(x, f, sig, hold, cost_mode, secs):
    """Simulate quarter by quarter (positions never cross a session, so this is exact) with the quarter's causal stop
    and cost. Returns days, trades (with gross pnl and ATR at entry)."""
    qs = x.index.to_period('Q')
    atr_q = f.atr.groupby(qs).median()
    prev = atr_q.shift(1).fillna(atr_q)
    ref = f.atr[(f.index >= M1START)].median()
    D, T = [], []
    for qq in atr_q.index:
        sel = qs == qq
        xq = x[sel]; A = Arr(xq); sq = np.asarray(sig)[sel]
        sl = SL_ATR * prev[qq]
        if cost_mode == 'gross': c = 0.0
        elif cost_mode == 'vol': c = COST * prev[qq] / ref
        else: c = float(cost_mode)
        d, t = run(A, sq, 1000.0, sl, hold, 2, spr=c, secs=secs, use_spread=False)
        t = t.assign(atr=f.atr.values[sel][t.ei.values], cost=c, sl=sl, stop=(t.pnl <= -sl + 1e-6 - c) | (t.pnl <= -sl * 0.999))
        D.append(d); T.append(t)
    return pd.concat(D), pd.concat(T, ignore_index=True)


def period_stats(d, t, a, b):
    r = summ(d, t, a, b)
    tt = t[(t.entry >= a) & (t.entry < b)]
    r['gross_atr'] = ((tt.pnl + tt.cost) / tt.atr).mean() if len(tt) else np.nan
    r['gross_tr'] = (tt.pnl + tt.cost).mean() if len(tt) else np.nan
    r['stop_share'] = tt.stop.mean() if len(tt) else np.nan
    return r


if __name__ == '__main__':
    out = []
    qrows = []
    for tf in ('M5', 'M15'):
        x = load_tf(tf); f = feats(x); secs = SECS[tf]
        Ks = {}
        for port, k, hold, ext in (('A', 1, 1, False), ('B', 3, 3, False), ('C', 1, 1, True)):
            for qm in ((0.5, 1.0, 2.0) if port in 'AB' else (1.0,)):
                Ks[(port, qm)] = (k, hold, ext, calib_K(f, k, Q_P1 * qm, ext))
        Ks[('L', 1.0)] = (3, 3, False, K_LIT)
        print(f'\n===== {tf}: {x.index[0]} .. {x.index[-1]}  ({len(x)} bars); thresholds K (x ATR{ATR_N}): ' +
              ', '.join(f'{p}{qm:g}q={v[3]:.2f}' for (p, qm), v in Ks.items()))
        for (port, qm), (k, hold, ext, K) in Ks.items():
            s = signal(f, k, K, ext)
            for cm in ('gross', COST, 0.30, 'vol'):
                d, t = run_q(x, f, s, hold, cm, secs); NCFG += 1
                for pname, a, b in PERIODS[tf]:
                    r = period_stats(d, t, a, b)
                    r.update(tf=tf, port=port, qmult=qm, K=K, k=k, hold=hold, cost=str(cm), period=pname)
                    out.append(r)
                if cm == COST and qm == 1.0:
                    # baselines on the same bars
                    rnd = {p[0]: [] for p in PERIODS[tf]}
                    for z in range(20):
                        dz, tz = run_q(x, f, random_like(s, z), hold, cm, secs)
                        for pname, a, b in PERIODS[tf]: rnd[pname].append(summ(dz, tz, a, b)['per_day'])
                    dl, tl = run_q(x, f, np.where(s != 0, 1.0, 0.0), hold, cm, secs)
                    ds, ts = run_q(x, f, np.where(s != 0, -1.0, 0.0), hold, cm, secs)
                    for pname, a, b in PERIODS[tf]:
                        r = period_stats(d, t, a, b); rr = np.array(rnd[pname])
                        print(f'  {port} q{qm:g} K {K:.2f} hold {hold} | {pname:36s} {r["per_day"]:+6.2f}/day {r["trades_day"]:5.1f} tr/d '
                              f'{r["per_trade"]:+.3f}/tr gross {r["gross_tr"]:+.3f}/tr ({r["gross_atr"]:+.3f} ATR) win {r["win"]:.2f} '
                              f'losing days {r["losing_days"]:.2f} worst day {r["worst_day"]:+6.1f} maxDD {r["max_dd"]:+7.1f} '
                              f'stops {r["stop_share"]:.3f} long {r["long_share"]:.2f} | random {rr.mean():+.2f} (sd {rr.std():.2f}, '
                              f'share>=pick {np.mean(rr >= r["per_day"]):.2f}) long-only {summ(dl, tl, a, b)["per_day"]:+.2f} '
                              f'short-only {summ(ds, ts, a, b)["per_day"]:+.2f}')
                    # quarter table
                    qs = d.index.to_period('Q')
                    rq = {}
                    for z in range(20):
                        dz, _ = run_q(x, f, random_like(s, z), hold, cm, secs)
                        for qq, v in dz.pnl.groupby(dz.index.to_period('Q')).mean().items(): rq.setdefault(qq, []).append(v)
                    for qq in sorted(set(qs)):
                        dq = d[qs == qq]; tq = t[t.entry.dt.to_period('Q') == qq]
                        qrows.append(dict(tf=tf, port=port, K=K, quarter=str(qq), days=len(dq), per_day=dq.pnl.mean(),
                                          trades_day=len(tq) / max(len(dq), 1), per_trade=tq.pnl.mean(),
                                          gross_tr=(tq.pnl + tq.cost).mean(), gross_atr=((tq.pnl + tq.cost) / tq.atr).mean(),
                                          random_per_day=np.mean(rq[qq]), random_sd=np.std(rq[qq])))
    R = pd.DataFrame(out); R.to_csv(OUT + 'h1_history_results.csv', index=False)
    Q = pd.DataFrame(qrows); Q.to_csv(OUT + 'h1_history_quarters.csv', index=False)
    pd.set_option('display.width', 250)
    print('\n--- all ports x thresholds x costs: $/day by period (rows = port, q multiple, cost) ---')
    pv = R.pivot_table(index=['tf', 'port', 'qmult', 'cost'], columns='period', values='per_day', aggfunc='first')
    print(pv.round(2).to_string())
    print('\n--- gross $/trade in ATR units (cost-free; > 0 means the fade direction is right on average) ---')
    print(R[R.cost == 'gross'].pivot_table(index=['tf', 'port', 'qmult'], columns='period', values='gross_atr', aggfunc='first').round(3).to_string())
    print('\n--- quarter by quarter at $0.20 (q = P1 rate; L = literal) ---')
    Q['pnl_vs_random'] = Q.per_day - Q.random_per_day
    for (tf, port), g in Q.groupby(['tf', 'port']):
        print(f'{tf} {port}: ' + ' '.join(f'{r.quarter}:{r.per_day:+.2f}({r.trades_day:.1f}t,g{r.gross_atr:+.2f},rnd{r.random_per_day:+.2f})' for r in g.itertuples()))
        pre = g[~g.quarter.isin(['2026Q3', '2026Q4'])]
        print(f'   quarters before the M1 file: {len(pre)}, positive after $0.20: {(pre.per_day > 0).sum()}, '
              f'beating random mean: {(pre.pnl_vs_random > 0).sum()}, gross ATR > 0: {(pre.gross_atr > 0).sum()}')
    print('\nhistory configurations scored (port x threshold x cost, each over all periods):', NCFG)
