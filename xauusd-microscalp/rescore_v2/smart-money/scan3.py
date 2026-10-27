"""Family-wide TRAIN bracket check: every scan2 variant (base x session x trend x vol x direction, n_day>=3)
run through 3 fixed brackets (FAIR fills, base spread, max_open 3), next to its random-direction twin
(same bars). If the SMC per-trade distribution looks like the twins', the family has no edge."""
import sys, itertools, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from base_sigs import *
from mlib import Harness, spread_series, _sim, FILL, random_like

t0 = time.time()
H = Harness(); m1 = H.m1
base = build_base(H)
S = sessions(m1); TRD = {'m15': trend_m15(m1), 'h1': trend_h1(m1)}; VOL = vol_regime(m1)
TR = m1.index < SPLIT
ntr = int(TR.sum()); ND = int((H.dates < SPLIT).sum())
spr = H._spr['base']
BR = ((0.3, 1.0, 3), (0.5, 2.0, 5), (1.0, 3.0, 10))


def run(sig, tp, sl, to, mo=3):
    dp, dt, ti, to_, tpn, tdr = _sim(H.o, H.h, H.l, H.c, spr, H.tod, H.day, sig.astype(np.int64), tp, sl, to, mo,
                                     FILL['FAIR'], 0.0, 0.0, 0)
    k = ti < ntr
    return dp[:ND].mean(), tpn[k].mean() if k.any() else np.nan, k.sum() / ND


rows = []
for name, s0 in base.items():
    for sign in (1, -1):
        s = (sign * s0).astype(np.int64)
        for sess, tr_f, vf in itertools.product(S, ('all', 'with_m15', 'anti_m15', 'with_h1', 'anti_h1'), ('all', 'hi', 'lo')):
            msk = (s != 0) & S[sess]
            if tr_f != 'all':
                t = TRD[tr_f.split('_')[1]]
                msk &= (s * t > 0) if tr_f.startswith('with') else (s * t < 0)
            if vf != 'all':
                msk &= (VOL == (1 if vf == 'hi' else -1))
            if (msk & TR).sum() / ND < 3: continue
            sig = np.where(msk, s, 0)
            rnd = random_like(sig, len(rows))
            r = dict(sig=name, dir=sign, sess=sess, trend=tr_f, vol=vf)
            for j, (tp, sl, to) in enumerate(BR):
                r[f'pd{j}'], r[f'pt{j}'], r[f'n{j}'] = run(sig, tp, sl, to)
                r[f'rpd{j}'], r[f'rpt{j}'], _ = run(rnd, tp, sl, to)
            rows.append(r)
df = pd.DataFrame(rows)
df.to_csv('/mnt/project-files/xauusd-microscalp/families/smart-money/scan3_train.csv.gz', index=False)
print('variants', len(df), 'x', len(BR), 'brackets x 2 (signal + random twin) in', round(time.time() - t0), 's')
pd.set_option('display.width', 250)
for j, b in enumerate(BR):
    print(f'\nbracket tp/sl/timeout={b}: per_trade distribution, SMC variants vs random-direction twins (TRAIN)')
    print(pd.DataFrame({'smc_pt': df[f'pt{j}'].describe(percentiles=[.1, .5, .9, .99]),
                        'rand_pt': df[f'rpt{j}'].describe(percentiles=[.1, .5, .9, .99]),
                        'smc_pd': df[f'pd{j}'].describe(percentiles=[.1, .5, .9, .99]),
                        'rand_pd': df[f'rpd{j}'].describe(percentiles=[.1, .5, .9, .99])}).round(3).T.to_string())
    print('  share with TRAIN per_day > 0: smc', round((df[f'pd{j}'] > 0).mean(), 3), ' random', round((df[f'rpd{j}'] > 0).mean(), 3))
    print('  top 5:')
    print(df.sort_values(f'pd{j}', ascending=False)[['sig', 'dir', 'sess', 'trend', 'vol', f'n{j}', f'pt{j}', f'pd{j}', f'rpd{j}']].head(5).round(3).to_string(index=False))
