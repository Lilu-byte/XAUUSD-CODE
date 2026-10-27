"""Long-history check of the SAME rule shapes on other data (not the M1 rules themselves: there is no older M1).
P1 analog: onset of a run of >= 4 same-colour bars totalling > 4 x A240 (A = mean bar range, 240 bars of that TF), faded,
           next-bar-open entry, time exit after 3 bars, no TP, fixed disaster stop.
P2 analog: RSI3 > 97.5 and z60 > 2 (sell) / RSI3 < 2.5 and z60 < -2 (buy), every bar, time exit 5 bars, max_open 3.
M5 2025-05-05..2026-06-25 and M15 2022..2026-06-25 are before the M1 sample, so they are clean history; the
M5/M15 bars inside the M1 period are shown separately. Same engine (_sim_next), same entry filters, spread
'base' (recorded bar spread + $0.05; on M5/M15 the recorded spread is the lowest in 5/15 minutes, so optimistic)
and flat $0.30. Random directions on the same bars: 20 seeds."""
import sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-stretch')
from feats import *
from simlib import EASim, random_like
from mlib import _read, OTHER

M1_START = pd.Timestamp('2026-06-26')


def load_tf(tf):
    d = _read(OTHER[tf])
    sp = d.spread.copy()
    med = sp[sp > 0].groupby(sp[sp > 0].index.hour).median()
    zero = sp <= 0
    sp[zero] = d.index[zero].hour.map(med).values
    d['spread_usd'] = sp * 0.01
    d['tod'] = d.index.hour * 60 + d.index.minute
    nxt = d.index.to_series().shift(-1)
    d['last_of_session'] = ((nxt - d.index.to_series()) > pd.Timedelta(minutes=30)) | nxt.isna()
    return d


def feats_tf(d):
    f = pd.DataFrame(index=d.index)
    f['A'] = (d.high - d.low).rolling(240).mean()
    C = d.close; mu = C.rolling(60).mean(); sd = C.rolling(60).std(ddof=0); f['z60'] = (C - mu) / sd.where(sd > 0)
    dd = C.diff(); up = dd.clip(lower=0).ewm(alpha=1 / 3, adjust=False).mean(); dn = (-dd).clip(lower=0).ewm(alpha=1 / 3, adjust=False).mean()
    f['rsi3'] = 100 * up / (up + dn).where((up + dn) > 0)
    col = np.sign(C - d.open).values; st = np.zeros(len(C)); first = np.zeros(len(C), np.int64)
    for i in range(len(C)):
        if col[i] != 0 and i > 0 and np.sign(st[i - 1]) == col[i]: st[i] = st[i - 1] + col[i]; first[i] = first[i - 1]
        else: st[i] = col[i]; first[i] = i
    f['streak'] = st; f['runmv'] = C.values - d.open.values[first]
    return f


def per(days, trades, lo, hi):
    dd = days[(days.index >= lo) & (days.index < hi)]; tt = trades[(trades.entry >= lo) & (trades.entry < hi)]
    return dd.pnl.mean(), len(tt) / max(len(dd), 1), tt.pnl.mean() if len(tt) else np.nan, (dd.pnl < 0).mean(), dd.pnl.min()


if __name__ == '__main__':
    onset = lambda s0: np.where(np.r_[0, s0[:-1]] == s0, 0, s0)
    ncfg = 0
    for tf, sls in (('M5', (25, 1000)), ('M15', (40, 1000))):
        d = load_tf(tf); E = EASim(d); f = feats_tf(d)
        ok = np.isfinite(f.A.values) & np.isfinite(f.z60.values) & E.ok
        st = f.streak.values; mv = f.runmv.values; a = f.A.values
        p1 = onset(np.where((st >= 4) & (mv > 4 * a), -1, np.where((st <= -4) & (mv < -4 * a), 1, 0)).astype(float))
        p2 = np.where((f.rsi3.values > 97.5) & (f.z60.values > 2), -1, np.where((f.rsi3.values < 2.5) & (f.z60.values < -2), 1, 0)).astype(float)
        start = d.index[240]
        segs = [('pre-M1', start, M1_START)]
        yrs = sorted(set(d.index[d.index < M1_START].year))
        segs += [(f'{y}', max(pd.Timestamp(f'{y}-01-01'), start), min(pd.Timestamp(f'{y + 1}-01-01'), M1_START)) for y in yrs]
        segs += [('M1-TRAIN dates', M1_START, SPLIT)] + ([('M1-TEST dates', SPLIT, pd.Timestamp('2026-12-31'))] if '--with-test' in sys.argv else [])
        print(f'===== {tf}: {d.index[0].date()}..{d.index[-1].date()}, A240 median ${np.nanmedian(a):.2f}')
        for nm, s, N, mo in (('P1-analog run4 4A onset, exit 3 bars', p1, 3, 1), ('P2-analog RSI3 97.5 & z60 2, exit 5 bars', p2, 5, 3)):
            s = np.where(ok, s, 0)
            for sl in sls:
                for spm in ('base', 'wide'):
                    dy, tr = E.run(s, tp=1000, sl=sl, timeout=N, max_open=mo, spread=spm); ncfg += 1
                    out = []
                    for sn, lo, hi in segs:
                        pdy, td, pt, lose, worst = per(dy, tr, lo, hi)
                        out.append(f'{sn} {pdy:+.2f}/d {td:.1f}t/d {pt:+.3f}/t')
                    rnd = ''
                    if spm == 'base':
                        rr = []
                        for z in range(20):
                            dz, tz = E.run(random_like(s, z), tp=1000, sl=sl, timeout=N, max_open=mo); ncfg += 1
                            rr.append(per(dz, tz, start, M1_START)[0])
                        rnd = f' | random dirs pre-M1 {np.mean(rr):+.2f}/d (sd {np.std(rr):.2f})'
                        dl, tl = E.run(np.abs(s), tp=1000, sl=sl, timeout=N, max_open=mo); ds, ts = E.run(-np.abs(s), tp=1000, sl=sl, timeout=N, max_open=mo); ncfg += 2
                        rnd += f', always-long {per(dl, tl, start, M1_START)[0]:+.2f}, always-short {per(ds, ts, start, M1_START)[0]:+.2f}'
                        rnd += f', long share {(tr[(tr.entry < M1_START)].dir == 1).mean():.2f}'
                    print(f'{nm} SL {sl} spread {spm}:'); print('   ' + ' | '.join(out) + rnd)
    print(ncfg, 'simulations')
