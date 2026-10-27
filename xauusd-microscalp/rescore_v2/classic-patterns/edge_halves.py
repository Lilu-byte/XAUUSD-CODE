"""Stage 2 (TRAIN only): split TRAIN into A = Jun26-Jul31 and B = Aug. For every config compute net
move (move - spread) at each horizon in A and B. Robust = positive in both halves at the same horizon.
Also: how many 'robust' configs would chance produce? (compare with random-direction signals)."""
from pats import *
H = Harness(); m = H.m1
ok = m.tod.values < END_TOD - 15
A = ok & (m.index < pd.Timestamp('2026-08-01')); B = ok & (m.index >= pd.Timestamp('2026-08-01')) & (m.index < SPLIT)
nA = len(np.unique(m.index[A].date)); nB = len(np.unique(m.index[B].date))
spr = spread_series(m, 'base')
HZ = (1, 2, 3, 5, 10)
FWD = {k: (m.close.shift(-k) - m.close).values for k in HZ}
TRD = {tf: trend(m, tf) for tf in ('M15', 'H1')}

def net(sig, msk0):
    msk = msk0 & (sig != 0); out = []
    for k in HZ:
        f = FWD[k][msk] * sig[msk] - spr[msk]
        out.append(np.nanmean(f) if msk.sum() > 10 else np.nan)
    return np.array(out), msk.sum()

rows = []
for tfk, mode in ((1, 'fixed'), (2, 'fixed'), (2, 'rolling'), (3, 'fixed'), (3, 'rolling')):
    S = on_m1(m, tfk, mode)
    for name, s in S.items():
        for filt in ('none', 'M15_with', 'M15_against', 'H1_with', 'H1_against'):
            if filt == 'none': base = s
            else:
                tf, w = filt.split('_'); t = TRD[tf]
                base = np.where((np.sign(s) == t) if w == 'with' else (np.sign(s) == -t), s, 0)
            for dirn, mult in (('follow', 1), ('fade', -1)):
                sg = np.sign(base) * mult
                a, na = net(sg, A); b, nb = net(sg, B)
                r = dict(tf=f'M{tfk}', mode=mode, pattern=name, filt=filt, dir=dirn, dayA=na / nA, dayB=nb / nB)
                for i, k in enumerate(HZ): r[f'A{k}'] = a[i]; r[f'B{k}'] = b[i]
                r['robust_min'] = np.nanmax(np.minimum(a, b)) if not np.all(np.isnan(np.minimum(a, b))) else np.nan
                r['robust_h'] = HZ[int(np.nanargmax(np.minimum(a, b)))] if not np.isnan(r['robust_min']) else -1
                rows.append(r)
df = pd.DataFrame(rows); df.to_csv('edge_halves_train.csv', index=False)
pd.set_option('display.width', 250)
q = df[(df.dayA >= 1) & (df.dayB >= 1)]
print('configs', len(df), 'with >=1/day in both halves', len(q))
print('robust (net>0 both halves at some horizon):', (q.robust_min > 0).sum(), ' at horizon<=3:',
      ((q[[f'A{k}' for k in (1,2,3)]].values > 0) & (q[[f'B{k}' for k in (1,2,3)]].values > 0)).any(1).sum())
print(q.sort_values('robust_min', ascending=False)[['tf','mode','pattern','filt','dir','dayA','dayB','A1','B1','A2','B2','A3','B3','A5','B5','A10','B10','robust_min','robust_h']].head(30).round(3).to_string(index=False))
# chance baseline: random direction on the same bars, robust count
cnt = []
for seed in range(3):
    c = 0
    for tfk, mode in ((1, 'fixed'), (2, 'fixed'), (3, 'fixed')):
        S = on_m1(m, tfk, mode)
        for name, s in S.items():
            sg = random_like(s, seed + 100 * tfk)
            a, na = net(sg, A); b, nb = net(sg, B)
            if na / nA >= 1 and nb / nB >= 1 and np.nanmax(np.minimum(a, b)) > 0: c += 1
    cnt.append(c)
print('random-direction robust count per 81 signal sets (3 seeds):', cnt)
print('real robust count among the same 81 unfiltered follow sets:', (q[(q.filt=='none')&(q.dir=='follow')&(q['mode']=='fixed')].robust_min>0).sum(),
      'fade:', (q[(q.filt=='none')&(q.dir=='fade')&(q['mode']=='fixed')].robust_min>0).sum())
