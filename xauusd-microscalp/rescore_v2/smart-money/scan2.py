"""Edge scan #2 (TRAIN only): base SMC signals x session x HTF-trend x volatility filters, plus combined
entry models (sweep -> displacement / FVG) and 'forming candle' sweeps. Writes scan2_train.csv."""
import sys, itertools, time
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from sigs2 import *
from mlib import Harness, spread_series

t0 = time.time()
H = Harness(); m1 = H.m1; spr = spread_series(m1, 'base'); o, h, l, c = arrs(m1)
idx = m1.index; TR = idx < SPLIT; HA = TR & (idx < pd.Timestamp('2026-08-01')); HB = TR & ~HA
ND = len(np.unique(idx[TR].date))
HZ = (1, 2, 3, 5, 10, 20)
F = {}
for k in HZ:
    f = np.full(len(c), np.nan); f[:-k] = c[k:] - c[:-k]; F[k] = f

b5, p5 = htf_bars(m1, 5); O5, H5, L5, C5 = arrs(b5)
P = lambda s: place(m1, p5, s)
base = {}
for N in (5, 15, 30, 60):
    base[f'sweep_M1_N{N}_strict'] = sweep(o, h, l, c, N, 0.3, True, 0.3)
    base[f'sweep_M1_N{N}_loose'] = sweep(o, h, l, c, N)
for N in (10, 30, 45):
    base[f'sweep_M5_N{N}'] = P(sweep(O5, H5, L5, C5, N, 0.66, False, 0.3))
for N, bk in itertools.product((6, 12, 24), (0.0, 0.3)):
    base[f'sweepform_M5_N{N}_b{bk}'] = sweep_forming(m1, N, 5, bk)
for k in (3, 5, 8):
    base[f'swsweep_M1_k{k}'] = swing_sweep(o, h, l, c, k)
for k in (3, 5):
    base[f'swsweep_M5_k{k}'] = P(swing_sweep(O5, H5, L5, C5, k, 48))
for N, W, cf in itertools.product((15, 30, 60), (5, 15), (0, 1, 2)):
    base[f'sweepthen_N{N}_W{W}_c{cf}'] = sweep_then(o, h, l, c, N, W, cf, 0.2)
for g in (0.5, 1.0, 2.0):
    base[f'fvgret_M1_g{g}'] = fvg_retrace(o, h, l, c, g, 15, 0)
for g in (0.2, 0.5):
    base[f'fvgret_M5_g{g}'] = P(fvg_retrace(O5, H5, L5, C5, g * 2.2, 15, 0))
for k in (5, 8):
    base[f'ob_M1_k{k}'] = structure(o, h, l, c, k, 30, kind=2)
for k in (3, 5):
    base[f'ob_M5_k{k}'] = P(structure(O5, H5, L5, C5, k, 10, kind=2))
for k in (2, 3):
    base[f'bos_M5_k{k}'] = P(structure(O5, H5, L5, C5, k, kind=0))
base['choch_M5_k3'] = P(structure(O5, H5, L5, C5, 3, kind=3))
for N in (30, 60):
    base[f'brk_M5_N{N}'] = P(breakout(O5, H5, L5, C5, N))
    base[f'brk_M1_N{N}'] = breakout(o, h, l, c, N)
for st, e in itertools.product((5, 10), (0.2, 0.5)):
    base[f'rnrej_{st}_e{e}'] = round_level(o, h, l, c, st, 'reject', e)
pdh, pdl = day_levels(m1)
base['pdhl_sweep'] = level_events(m1, H.day, pdh, pdl, 0, 0.0, 3)
base['pdhl_break'] = level_events(m1, H.day, pdh, pdl, 1, 0.0, 3)
ah, al = session_range(m1, 60, 600)
base['asia_sweep'] = level_events(m1, H.day, ah, al, 0, 0.0, 3)
base['asia_break'] = level_events(m1, H.day, ah, al, 1, 0.0, 3)
print('base signals', len(base), 'built in', round(time.time() - t0), 's')

S = sessions(m1)
TRD = {'m15': trend_m15(m1), 'h1': trend_h1(m1)}
VOL = vol_regime(m1)
rows = []
for name, s0 in base.items():
    for sign in (1, -1):
        s = (sign * s0).astype(float)
        for sess, tr_f, vf in itertools.product(S, ('all', 'with_m15', 'anti_m15', 'with_h1', 'anti_h1'), ('all', 'hi', 'lo')):
            msk = (s != 0) & S[sess]
            if tr_f != 'all':
                t = TRD[tr_f.split('_')[1]]
                msk &= (s * t > 0) if tr_f.startswith('with') else (s * t < 0)
            if vf != 'all':
                msk &= (VOL == (1 if vf == 'hi' else -1))
            mt = msk & TR
            if mt.sum() < 60: continue
            r = dict(sig=name, dir=sign, sess=sess, trend=tr_f, vol=vf, n_day=mt.sum() / ND, spr=spr[mt].mean())
            for k in HZ:
                a = (F[k] * s)
                x = a[mt]; x = x[~np.isnan(x)]
                r[f'mv{k}'] = x.mean(); r[f'se{k}'] = x.std() / np.sqrt(len(x))
                xa = a[msk & HA]; xb = a[msk & HB]
                r[f'a{k}'] = np.nanmean(xa); r[f'b{k}'] = np.nanmean(xb)
            rows.append(r)
df = pd.DataFrame(rows)
df.to_csv('/mnt/project-files/xauusd-microscalp/families/smart-money/scan2_train.csv.gz', index=False)
print('variants evaluated', len(df), 'in', round(time.time() - t0), 's')
pd.set_option('display.width', 250)
for k in HZ:
    df[f't{k}'] = (df[f'mv{k}'] - df.spr) / df[f'se{k}']
    df[f'z{k}'] = df[f'mv{k}'] / df[f'se{k}']
print('\nDistribution of raw z = move/se (null ~ N(0,1) if no signal), per horizon, n_day>=3:')
d3 = df[df.n_day >= 3]
print(pd.DataFrame({k: d3[f'z{k}'].describe(percentiles=[.5, .9, .99]) for k in HZ}).round(2).to_string())
for k in (1, 3, 5, 10, 20):
    d = d3[(d3[f'a{k}'] > d3.spr) & (d3[f'b{k}'] > d3.spr)].sort_values(f't{k}', ascending=False)
    print(f'\n== h={k}m  n_day>=3, both TRAIN halves beat spread: {len(d)} of {len(d3)}; top 10 by t(move-spread)')
    print(d[['sig', 'dir', 'sess', 'trend', 'vol', 'n_day', 'spr', f'mv{k}', f'a{k}', f'b{k}', f'z{k}', f't{k}']].head(10).round(3).to_string(index=False))
