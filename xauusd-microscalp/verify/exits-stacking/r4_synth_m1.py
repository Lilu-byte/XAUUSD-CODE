"""Step 4c: run the EXACT M1 rule (MR signal on M1 + grid) on synthetic M1 bars made from the real M5 file, so that the
14 months BEFORE the M1 file starts (2025-05-05..2026-06-25) can be used.
Each M5 bar O/H/L/C is split into 5 M1 bars by a Brownian bridge O -> C (20 sub-steps per minute) whose up/down excursions
are rescaled to touch exactly H and L; M1 open/high/low/close are read off the path. The synthetic bars respect every
real M5 OHLC exactly; only the within-5-minute ordering is invented.
Validation: build the same synthetic M1 for the months where REAL M1 exists and compare the rule's results with the real-M1
results (signals/day, baskets/day, per day, deep baskets, failures). Several synthetic realisations."""
from common import *
from numba import njit
import time

pd.set_option('display.width', 250)


@njit(cache=True)
def synth(o, h, l, c, sub, seed):
    np.random.seed(seed)
    n = len(o); m = 5 * sub
    O = np.empty(5 * n); Hh = np.empty(5 * n); Ll = np.empty(5 * n); C = np.empty(5 * n)
    z = np.zeros(m + 1); px = np.zeros(m + 1)
    for b in range(n):
        if h[b] - l[b] < 1e-9:
            for k in range(5):
                O[5 * b + k] = o[b]; Hh[5 * b + k] = o[b]; Ll[5 * b + k] = o[b]; C[5 * b + k] = o[b]
            continue
        for j in range(1, m + 1):
            z[j] = z[j - 1] + np.random.normal()
        zN = z[m]
        for j in range(m + 1):
            z[j] = z[j] - zN * j / m
        au = 1e18; ad = 1e18; jmax = -1; jmin = -1; zmx = 0.0; zmn = 0.0
        for j in range(1, m):
            ln = o[b] + (c[b] - o[b]) * j / m
            if z[j] > 1e-12:
                r = (h[b] - ln) / z[j]
                if r < au: au = r
            if z[j] < -1e-12:
                r = (ln - l[b]) / (-z[j])
                if r < ad: ad = r
            if z[j] > zmx: zmx = z[j]; jmax = j
            if z[j] < zmn: zmn = z[j]; jmin = j
        if au > 1e17: au = 0.0
        if ad > 1e17: ad = 0.0
        for j in range(m + 1):
            ln = o[b] + (c[b] - o[b]) * j / m
            px[j] = ln + (au * z[j] if z[j] > 0 else ad * z[j])
        px[0] = o[b]; px[m] = c[b]
        # make sure H and L are touched
        hi = -1e18; lo = 1e18
        for j in range(m + 1):
            if px[j] > hi: hi = px[j]
            if px[j] < lo: lo = px[j]
        if hi < h[b] - 1e-9:
            jj = jmax if jmax > 0 else 1 + int(np.random.random() * (m - 1))
            px[jj] = h[b]
        if lo > l[b] + 1e-9:
            jj = jmin if jmin > 0 else 1 + int(np.random.random() * (m - 1))
            if px[jj] == h[b]:
                jj = 1 + (jj % (m - 1))
            px[jj] = l[b]
        for k in range(5):
            a = k * sub; e = (k + 1) * sub
            mx = -1e18; mn = 1e18
            for j in range(a, e + 1):
                if px[j] > mx: mx = px[j]
                if px[j] < mn: mn = px[j]
            O[5 * b + k] = np.round(px[a] * 100) / 100; C[5 * b + k] = np.round(px[e] * 100) / 100
            Hh[5 * b + k] = np.round(mx * 100) / 100; Ll[5 * b + k] = np.round(mn * 100) / 100
    return O, Hh, Ll, C


def m5_to_m1(m5, seed, sub=20):
    O, Hh, Ll, C = synth(m5.open.values, m5.high.values, m5.low.values, m5.close.values, sub, seed)
    idx = (m5.index.values[:, None] + (np.arange(5) * np.timedelta64(1, 'm'))[None, :]).ravel()
    d = pd.DataFrame({'open': O, 'high': Hh, 'low': Ll, 'close': C}, index=pd.DatetimeIndex(idx))
    d['spread_usd'] = np.repeat(m5.spread_usd.values, 5)
    d['tod'] = d.index.hour * 60 + d.index.minute
    nxt = d.index.to_series().shift(-1)
    d['last_of_session'] = ((nxt - d.index.to_series()) > pd.Timedelta(minutes=30)) | nxt.isna()
    return d


def prep_m5():
    d = mlib.load('M5').copy()
    sp = d.spread.copy(); med = sp[sp > 0].groupby(sp[sp > 0].index.hour).median(); z = sp <= 0
    sp[z] = d.index[z].hour.map(med).values
    d['spread_usd'] = sp * 0.01
    return d


M1_START = pd.Timestamp('2026-06-26'); SPLIT = mlib.SPLIT
PER = [('pre-M1 2025-05..2026-06-25', None, M1_START), ('M1-TRAIN months', M1_START, SPLIT), ('M1-TEST months', SPLIT, None)]

if __name__ == '__main__':
    m5 = prep_m5()
    m1r = mlib.load_m1(); gr = G(m1r)
    mr_r = mr_signal(m1r)
    # real M1 reference (FAIR path seeds 0..2) on wide 0.30 spread, so real and synthetic use the same spread
    ref = {}
    for sp in ('wide', 'base'):
        runs = [gr.run(mr_r, seed=s, spread=sp) for s in range(3)]
        for name, lo, hi in PER[1:]:
            df = pd.DataFrame([summ(gr, *r, lo=lo, hi=hi) for r in runs])
            ref[(sp, name)] = df.mean(numeric_only=True)
            print(f'REAL M1 {sp:4s} {name:28s} per_day {df.per_day.mean():+7.2f} bsk/day {df.baskets_day.mean():5.1f} bwin {df.basket_win.mean():.4f} '
                  f'forced {df.n_forced.mean():.1f} worst_day {df.worst_day.min():+.0f} maxDDfloat {df.max_dd_float.min():+.0f} max_lev {df.max_levels.max()}')
    tr_ = (m1r.index >= M1_START)
    print(f'REAL M1 signals/day {(mr_r[tr_] != 0).sum() / len(np.unique(m1r.index[tr_].normalize())):.1f}; mean M1 range {(m1r.high - m1r.low)[tr_].mean():.3f}')

    rows = []; FAILS = []
    for rs in range(8):
        t0 = time.time()
        s1 = m5_to_m1(m5, seed=rs)
        gs = G(s1)
        sig = mr_signal(s1)
        ov = s1.index >= M1_START
        rng_ov = (s1.high - s1.low)[ov].mean()
        for sp in ('wide', 'base'):
            for ps in range(2):
                out = gs.run(sig, seed=ps, spread=sp)
                b = out[1]
                if sp == 'base' and ps == 0:
                    f = b[b.pnl < 0].assign(real=rs); FAILS.append(f)
                for name, lo, hi in PER:
                    r = summ(gs, *out, lo=lo, hi=hi)
                    r.update(real=rs, path_seed=ps, spread=sp, period=name)
                    rows.append(r)
        sd = (sig != 0)
        print(f'synthetic realisation {rs}: signals/day pre {sd[~ov].sum() / len(np.unique(s1.index[~ov].normalize())):.1f} overlap '
              f'{sd[ov].sum() / len(np.unique(s1.index[ov].normalize())):.1f}; mean synth M1 range (overlap) {rng_ov:.3f}  [{time.time() - t0:.0f}s]')
    R = pd.DataFrame(rows); R.to_csv(VOUT + 'r4_synth_m1.csv', index=False)
    F = pd.concat(FAILS); F.to_csv(VOUT + 'r4_synth_m1_failures.csv', index=False)
    agg = R.groupby(['spread', 'period']).agg(per_day=('per_day', 'mean'), per_day_min=('per_day', 'min'), per_day_max=('per_day', 'max'),
                                              bsk_day=('baskets_day', 'mean'), bwin=('basket_win', 'mean'), forced=('n_forced', 'mean'),
                                              forced_pnl=('forced_pnl', 'mean'), worst_day=('worst_day', 'median'),
                                              maxdd_closed=('max_dd_closed', 'median'), maxdd_float=('max_dd_float', 'median'),
                                              total=('total', 'mean'), days=('days', 'mean'))
    print(agg.round(2).to_string())
    print('\nshare of (realisation x path seed) runs with per_day < 0 in pre-M1 months:',
          R[R.period.str.startswith('pre')].groupby('spread').per_day.apply(lambda x: (x < 0).mean()).to_dict())
    print('\nfailed baskets (pnl<0), base spread, path seed 0, by realisation:')
    print(F.groupby('real').agg(n=('pnl', 'size'), total=('pnl', 'sum'), worst=('pnl', 'min')).round(0).to_string())
    print('\nworst failures across realisations:'); print(F.sort_values('pnl').head(15).to_string())
    print('\nfailure days (count of realisations with a failure that day):')
    fd = F.assign(day=F.start.dt.normalize()).groupby('day').agg(n_real=('real', 'nunique'), mean_pnl=('pnl', 'mean'))
    print(fd.sort_values('mean_pnl').round(0).head(25).to_string())
