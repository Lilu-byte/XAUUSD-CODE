"""Edge scan (TRAIN only) of SMC signal variants on M1 and M5. Prints the best by move-minus-spread
and writes scan1_train.csv. Test rows are never touched (edge_train masks to TRAIN)."""
import sys, itertools
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from sigs import *
from mlib import Harness, spread_series

H = Harness(); m1 = H.m1
spr = spread_series(m1, 'base')
o, h, l, c = arrs(m1)
rows = []


def rec(name, s, **p):
    for sign, tag in ((1, ''), (-1, '_inv')):
        r = edge_train(m1, sign * s.astype(np.int8), spr)
        r.update(name=name + tag, **p)
        rows.append(r)


TF = {}
for tf in (1, 5):
    if tf == 1:
        TF[tf] = (arrs(m1), None)
    else:
        b, pos = htf_bars(m1, tf)
        TF[tf] = (arrs(b), pos)


def put(tf, s):
    return s if tf == 1 else place(m1, TF[tf][1], s)


for tf in (1, 5):
    (O, Hh, Ll, C), _ = TF[tf]
    sc = 1.0 if tf == 1 else 2.2       # rough M5/M1 range ratio for $ thresholds
    # sweeps of prior N-bar extreme -> reversal
    for N, dep, col, cf in itertools.product((5, 10, 15, 20, 30, 45, 60), (0.0, 0.3), (False, True), (0.0, 0.3)):
        rec(f'sweep_M{tf}', put(tf, sweep(O, Hh, Ll, C, N, dep * sc, col, cf)), tf=tf, N=N, dep=dep, col=col, cf=cf)
    for N in (5, 10, 20, 30, 60):
        rec(f'brk_M{tf}', put(tf, breakout(O, Hh, Ll, C, N)), tf=tf, N=N)
    # fair value gaps
    for g in (0.0, 0.2, 0.5, 1.0, 2.0):
        rec(f'fvgimm_M{tf}', put(tf, fvg_imm(O, Hh, Ll, C, g * sc)), tf=tf, g=g)
        for W, mode in itertools.product((5, 15, 30), (0, 1)):
            rec(f'fvgret_M{tf}', put(tf, fvg_retrace(O, Hh, Ll, C, g * sc, W, mode)), tf=tf, g=g, W=W, mode=mode)
    # structure
    for k in (2, 3, 5, 8):
        rec(f'bos_M{tf}', put(tf, structure(O, Hh, Ll, C, k, kind=0)), tf=tf, k=k)
        rec(f'choch_M{tf}', put(tf, structure(O, Hh, Ll, C, k, kind=3)), tf=tf, k=k)
        for W in (10, 30):
            for tol in (0.0, 0.3):
                rec(f'retest_M{tf}', put(tf, structure(O, Hh, Ll, C, k, W, tol * sc, kind=1)), tf=tf, k=k, W=W, tol=tol)
            rec(f'ob_M{tf}', put(tf, structure(O, Hh, Ll, C, k, W, kind=2)), tf=tf, k=k, W=W)
        rec(f'swsweep_M{tf}', put(tf, swing_sweep(O, Hh, Ll, C, k)), tf=tf, k=k)

# round numbers (M1)
for step in (1, 5, 10, 25):
    rec('rn_break', round_level(o, h, l, c, step, 'break'), step=step)
    for e in (0.0, 0.2, 0.5):
        rec('rn_reject', round_level(o, h, l, c, step, 'reject', e), step=step, e=e)
    for e in (0.1, 0.3):
        if step > 1 or e < 0.5:
            rec('rn_near', round_level(o, h, l, c, step, 'near', e), step=step, e=e)

# prior day high/low, Asian range (server time GMT+3)
pdh, pdl = day_levels(m1)
for kind, e, mx in itertools.product((0, 1), (0.0, 0.5), (1, 3)):
    if kind == 1 and e > 0: continue
    rec('pdhl', level_events(m1, H.day, pdh, pdl, kind, e, mx), kind=kind, e=e, maxn=mx)
for a0, a1 in ((60, 540), (180, 600), (60, 600)):
    ah, al = session_range(m1, a0, a1)
    for kind, e, mx in itertools.product((0, 1), (0.0, 0.5), (1, 3)):
        if kind == 1 and e > 0: continue
        rec('asia', level_events(m1, H.day, ah, al, kind, e, mx), kind=kind, e=e, maxn=mx, a0=a0, a1=a1)

df = pd.DataFrame(rows)
df['best'] = df[['mv1', 'mv2', 'mv3', 'mv5', 'mv10']].max(axis=1)
df['net5'] = df.mv5 - df.spr
df['net3'] = df.mv3 - df.spr
df['net10'] = df.mv10 - df.spr
df.to_csv('/mnt/project-files/xauusd-microscalp/families/smart-money/scan1_train.csv.gz', index=False)
print('variants scanned:', len(df))
pd.set_option('display.width', 250)
cols = ['name', 'tf', 'N', 'dep', 'col', 'cf', 'g', 'W', 'mode', 'k', 'tol', 'step', 'e', 'kind', 'maxn', 'a0', 'a1',
        'n_day', 'spr', 'mv1', 'mv2', 'mv3', 'mv5', 'mv10', 'mv20', 'mv5_a', 'mv5_b', 'se5']
cols = [x for x in cols if x in df]
print('\nTop 30 by best-horizon move minus spread (n_day >= 3):')
d = df[df.n_day >= 3].copy(); d['bn'] = d.best - d.spr
print(d.sort_values('bn', ascending=False)[cols].head(30).round(3).to_string(index=False))
print('\nPer-family max of (best move - spread), n_day>=3:')
print(d.groupby('name').bn.max().sort_values(ascending=False).round(3).to_string())
