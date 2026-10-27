"""TRAIN-only edge scan: average move in the signal's direction over k M1 bars minus the
base spread paid, with a day-clustered t-stat and July/August halves. Writes edge_train.csv."""
import itertools, time, warnings
warnings.filterwarnings('ignore')
from sigs import *

HZ = (1, 2, 3, 5, 10, 15, 20, 30)
m = load_m1()
c = m.close.values
sb = spread_series(m, 'base')
tr = m.index < SPLIT
dayid = pd.factorize(m.index.normalize())[0]
half = np.where(m.index < pd.Timestamp('2026-08-01'), 0, 1)
ndays = len(np.unique(dayid[tr]))
FWD = {k: np.r_[c[k:] - c[:-k], np.full(k, np.nan)] for k in HZ}


def edge_train(s):
    mk = (s != 0) & tr
    n = mk.sum()
    r = dict(n=n, per_day=n / ndays, spr=sb[mk].mean() if n else np.nan)
    if n < 30: return r
    sd = s[mk]; dd = dayid[mk]; hh = half[mk]
    for k in HZ:
        mv = FWD[k][mk] * sd
        ok = ~np.isnan(mv)
        net = mv[ok] - sb[mk][ok]
        mu = net.mean()
        # cluster-robust SE by day
        g = pd.Series(net - mu).groupby(dd[ok]).sum().values
        se = np.sqrt((g ** 2).sum()) / len(net)
        r[f'mv{k}'] = mv[ok].mean(); r[f'net{k}'] = mu; r[f't{k}'] = mu / se if se > 0 else np.nan
        r[f'h0_{k}'] = net[hh[ok] == 0].mean(); r[f'h1_{k}'] = net[hh[ok] == 1].mean()
    return r


def main():
    t0 = time.time()
    D = ['T4', 'T4L', 'T4S', 'T5', 'T5L', 'T3', 'TH', 'T4D1', 'NY5', 'NY7', 'NY5x', 'T4NY']
    G = ['all', 'pb1', 'pb2', 'pb3', 'pbge2', 'rev1', 'rev2', 'rsi7_30', 'rsi3_15', 'rsi14_40', 'touch1', 'touch5',
         'below1', 'bo5', 'bo10', 'bo20', 'fade10', 'fade20', 'f5pb', 'f5go', 'mom1', 'mom3']
    S = ['all', 'ex1_3', 'lon', 'ny', 'lonny', 'day', 'asia']
    P = ['any', 'lo']
    dirs = {d: direction(d) for d in D}
    rows = []
    for dn, gn in itertools.product(D, G):
        base = trigger(gn, dirs[dn]) & (dirs[dn] != 0)
        for sn, pn in itertools.product(S, P):
            s = np.where(base & session(sn) & spreadf(pn), dirs[dn], 0)
            r = edge_train(s); r.update(dir=dn, trig=gn, sess=sn, spf=pn); rows.append(r)
    E = pd.DataFrame(rows)
    E.to_csv('edge_train.csv', index=False)
    print('combos', len(E), 'secs', round(time.time() - t0, 1))
    report(E)


def report(E):
    netc = [f'net{k}' for k in HZ]
    E = E.dropna(subset=netc)
    cols = ['dir', 'trig', 'sess', 'spf', 'per_day', 'spr', 'mv1', 'mv5', 'mv10', 'mv30', 'net5', 'net10', 'net30', 't10', 't30', 'h0_10', 'h1_10']
    pd.set_option('display.width', 250)
    print('\n== baseline (trigger=all, sess=all) ==')
    print(E[(E.trig == 'all') & (E.sess == 'all')][cols].round(3).to_string())
    print('\n== share of combos with net>0 at each horizon (per_day>=3) ==')
    q = E[E.per_day >= 3]
    print({k: round((q[f'net{k}'] > 0).mean(), 3) for k in HZ})
    print('\n== top 25 by net10 (per_day>=3) ==')
    print(q.sort_values('net10', ascending=False)[cols].head(25).round(3).to_string())
    print('\n== top 25 by net5 (per_day>=3) ==')
    print(q.sort_values('net5', ascending=False)[cols].head(25).round(3).to_string())
    print('\n== top 15 by net30 (per_day>=3) ==')
    print(q.sort_values('net30', ascending=False)[cols].head(15).round(3).to_string())


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'report': report(pd.read_csv('edge_train.csv'))
    else: main()
