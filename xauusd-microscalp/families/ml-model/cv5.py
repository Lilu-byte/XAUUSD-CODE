"""M5-history model (TRAIN only). Predict next 5 or 10 minutes at each M5 close using 16 months of M5 bars.
Walk-forward: foldA fit 2025-05..2025-12 -> val 2026-01..04; foldB fit ..2026-04 -> val 2026-05..08.
Metric: trailing top-q |score| (previous ~3 days of M5 scores), avg favourable move vs a flat $0.20 cost."""
import sys, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from feat5 import *
from feat import GROUPS, cols
from mods import *

OUT = '/mnt/project-files/xauusd-microscalp/families/ml-model/'
d = load('M5'); F = build5(d); T = d.index
tod = T.hour * 60 + T.minute
ok = (tod < 23 * 60 + 10) & (np.arange(len(d)) > 100) & (T < pd.Timestamp('2026-09-01'))
B = [pd.Timestamp(x) for x in ('2026-01-01', '2026-05-01', '2026-09-01')]
FSETS = {'all': list(GROUPS), 'noHTF': ['candle', 'ret', 'forming', 'ctx', 'flow'], 'candle+forming': ['candle', 'forming']}
G5 = dict(GROUPS); G5['forming'] = lambda c: c.startswith(('f15_', 'f60_')); G5['htf'] = lambda c: c.startswith(('M15_', 'H1_', 'H4_'))
GROUPS.update(G5)
COST = 0.20
QS = (0.01, 0.02, 0.05, 0.1, 0.2)
rows = []; t0 = time.time(); scores = {}
for n in [int(sys.argv[1])]:
    fwd = targets5(d, n).values
    for fs, groups in FSETS.items():
        cl = cols(F, groups)
        for kind in ('bin', 'binw', 'reg', 'logit'):
            s_all = np.full(len(d), np.nan)
            for fi in range(2):
                lo = B[fi]; hi = B[fi + 1]
                # purge: training rows must end n bars before the validation start (targets look forward)
                tr = ok & (T < lo - pd.Timedelta(minutes=5 * n)) & ~np.isnan(fwd)
                va = ok & (T >= lo) & (T < hi)
                m = fit(F.loc[tr, cl], fwd[tr], np.full(tr.sum(), COST), kind, n_estimators=300, min_child_samples=500)
                s_all[va] = score(m, F.loc[va, cl])
            idx = np.where(ok & (T >= B[0]))[0]; s = s_all[idx]; f = fwd[idx]
            scores[f'{n}|{fs}|{kind}'] = s.astype(np.float32)
            fo = np.where(T[idx] < B[1], 'A', 'B')
            for q in QS:
                sig = signal(s, roll_thr(s, q, window=800)); sel = (sig != 0) & ~np.isnan(f)
                g = sig[sel] * f[sel] - COST
                r = dict(n=n, fs=fs, kind=kind, q=q, n_day=sel.sum() / len(np.unique(T[idx].date)),
                         net=g.mean(), hit=(sig[sel] * f[sel] > 0).mean(), long=(sig[sel] > 0).mean())
                for fl in 'AB':
                    r['net_' + fl] = g[fo[sel] == fl].mean(); r['hit_' + fl] = (sig[sel] * f[sel] > 0)[fo[sel] == fl].mean()
                # the Jul-Aug part only (the M1 period)
                ja = (T[idx][sel] >= pd.Timestamp('2026-07-01'))
                r['net_JulAug'] = g[ja].mean()
                rows.append(r)
            print(f'n={n} {fs} {kind} {time.time() - t0:.0f}s', flush=True)
R = pd.DataFrame(rows); R.to_csv(OUT + f'cv5_val_n{sys.argv[1]}.csv', index=False)
np.savez_compressed(OUT + f'tmp_scores5_n{sys.argv[1]}.npz', idx=np.where(ok & (T >= B[0]))[0], **scores)
pd.set_option('display.width', 220)
print('configs', len(R))
print(R.pivot_table(index=['n', 'fs', 'kind'], columns='q', values='net').round(3))
print(R.sort_values('net', ascending=False).head(12).round(3).to_string(index=False))
