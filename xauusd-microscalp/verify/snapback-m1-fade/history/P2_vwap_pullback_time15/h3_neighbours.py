"""(2) Multiple testing on M1: the pick's rank in the family's TRAIN scans, and its neighbours (each parameter one step
either way, everything else as the pick), scored on TRAIN halves AND TEST (verification only -- nothing is selected).
Also structural controls: no VWAP gate, 'away' gate, VWAP side only (random bars, direction = sign(Close - VWAP)),
and holds beyond the family's grid edge (N = 15 was the longest hold scanned; k = 2.5 the lowest ATR multiple)."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/verify/snapback-m1-fade/history/P2_vwap_pullback_time15')
from p2v import *
import warnings; warnings.filterwarnings('ignore')

# --- family scan bookkeeping
S2 = pd.read_csv(FAM + 's2_scan_train.csv.gz'); S2b = pd.read_csv(FAM + 's2b_refine_train.csv.gz'); S3 = pd.read_csv(FAM + 's3_tp1_train.csv.gz')
S1 = pd.read_csv(FAM + 's1_edge_train.csv')
print(f'family TRAIN configurations: s1 edge cells {len(S1)}, s2 scan {len(S2)}, s2b refine {len(S2b)}, s3 TP<=1 {len(S3)}; '
      f'total {len(S1) + len(S2) + len(S2b) + len(S3)} (+32 history analogs, + robustness/TEST batteries)')
for nm, R in (('s2_scan', S2), ('s2b_refine', S2b)):
    R = R.copy(); R['minh'] = R[['pd_A', 'pd_B']].min(axis=1)
    q = (R.k == 3) & (R['mode'] == 'atr') & (R.th == 2.5) & (R.gate == 'toward' if 'gate' in R else R.region == 'toward') & (R.fresh == False) \
        & (R.sgate == 0.15) & (R.N == 15) & (R.sl == 25.0) & (R.mo == 3)
    if 'tp' in R: q &= (R.tp == 1000.0) & (R.be_trig == 0) & (R.trail == 0)
    if 'cd' in R: q &= R.cd == 0
    p = R[q].iloc[0]
    print(f'{nm}: pick TRAIN {p.pd_tr:+.2f}/day (halves {p.pd_A:+.2f}/{p.pd_B:+.2f}); rank by TRAIN $/day {(R.pd_tr > p.pd_tr).sum() + 1} of {len(R)}, '
          f'by min-half {(R.minh > p.minh).sum() + 1}; configs with both halves > 0: {((R.pd_A > 0) & (R.pd_B > 0)).mean():.2f}; '
          f'configs >= +5/day both halves: {((R.pd_A >= 5) & (R.pd_B >= 5)).sum()}')
    if 'gate' in R:
        for g in ('toward', 'none', 'away'):
            x = R[R.gate == g]; print(f'   gate {g:6s}: median TRAIN {x.pd_tr.median():+.2f}/day, share both halves>0 {((x.pd_A > 0) & (x.pd_B > 0)).mean():.2f}, n {len(x)}')

m = load_tf('M1'); A = Arr(m)
base = dict(k=2.5, L=3, atr_n=240, gate='toward', sgate=0.15)
sim0 = dict(sl=25.0, hold=15, mo=3)
V = [('PICK', {}, {})]
for k in (2.0, 2.25, 2.75, 3.0): V.append((f'k {k}', dict(k=k), {}))
for L in (2, 4): V.append((f'lookback {L} bars', dict(L=L), {}))
for n in (120, 180, 300, 480): V.append((f'ATR window {n}', dict(atr_n=n), {}))
for h in (10, 12, 18, 20, 30, 45, 60): V.append((f'hold {h} bars', {}, dict(hold=h)))
for sl in (10.0, 15.0, 40.0, 1000.0): V.append((f'stop ${sl:.0f}', {}, dict(sl=sl)))
for mo in (1, 2, 4, 5): V.append((f'max open {mo}', {}, dict(mo=mo)))
for sg in (0.0, 0.10, 0.20): V.append((f'spread gate {sg:.2f}', dict(sgate=sg), {}))
V.append(('cooldown 3 bars', {}, dict(cooldown=3)))
V.append(('cooldown 15 bars', {}, dict(cooldown=15)))
V.append(('latency 1 bar', {}, dict(latency=1)))
V.append(('gate none (plain fade)', dict(gate='none'), {}))
V.append(('gate away', dict(gate='away'), {}))
rows = []
for nm, sk, rk in V:
    s = A.signal(**{**base, **sk}); kw = {**sim0, **rk}
    d, t = A.run(s, **kw)
    tr, a_, b_, te = summ(d, t, None, SPLIT), summ(d, t, None, HALF), summ(d, t, HALF, SPLIT), summ(d, t, SPLIT, None)
    rr = np.array([summ(*A.run(random_like(s, z), **kw), SPLIT, None)['per_day'] for z in range(20)])
    rows.append(dict(variant=nm, train=tr['per_day'], A=a_['per_day'], B=b_['per_day'], test=te['per_day'], test_tr_day=te['trades_day'],
                     test_per_trade=te['per_trade'], test_worst_day=te['worst_day'], test_dd=te['max_dd'], test_long=te['long_share'],
                     test_rand=rr.mean(), test_share_rand_ge=(rr >= te['per_day']).mean()))
# VWAP side only: random eligible bars with the pick's count per day, direction = sign(Close - VWAP)
F = A.feats(3, 240); side = np.sign(A.c - F['vw'])
s0 = A.signal(); elig = (A.ea_filter(np.ones(len(m))) != 0) & (A.tod >= 65) & (A.tod <= 1349) & (side != 0) & (A.rec <= 0.15 + 1e-9)
cnt = pd.Series(s0 != 0).groupby(A.day).sum().values
VS = []
for z in range(20):
    rng = np.random.default_rng(500 + z); sb = np.zeros(len(m))
    for dd in range(len(A.dates)):
        idx = np.flatnonzero(elig & (A.day == dd))
        if cnt[dd] and len(idx): sb[rng.choice(idx, min(cnt[dd], len(idx)), replace=False)] = 1
    d, t = A.run(np.where(sb != 0, side, 0.0), **sim0)
    VS.append((summ(d, t, None, SPLIT)['per_day'], summ(d, t, None, HALF)['per_day'], summ(d, t, HALF, SPLIT)['per_day'], summ(d, t, SPLIT, None)['per_day']))
VS = np.array(VS)
rows.append(dict(variant='VWAP side only, random bars (20 seeds)', train=VS[:, 0].mean(), A=VS[:, 1].mean(), B=VS[:, 2].mean(), test=VS[:, 3].mean()))
R = pd.DataFrame(rows); R.to_csv(OUT + 'h3_neighbours.csv', index=False)
pd.set_option('display.width', 250)
print('\nM1 neighbours, base spread, FAIR, next-bar-open ($/day; TEST random = 20 seeds same bars):')
print(R.round(2).to_string(index=False))
nb = R[R.variant.str.match(r'(k |lookback|ATR window|hold 12|hold 18|stop \$15|stop \$40|max open [24]|spread gate)')]
print(f'\nneighbours (one step either way, {len(nb)}): TRAIN > 0 in {(nb.train > 0).sum()}, both halves > 0 in {((nb.A > 0) & (nb.B > 0)).sum()}, '
      f'TEST > 0 in {(nb.test > 0).sum()}, TEST >= +5/day in {(nb.test >= 5).sum()}, TEST beats >= 90% of random seeds in {(nb.test_share_rand_ge <= 0.10).sum()}; '
      f'TEST median {nb.test.median():+.2f}/day, TRAIN median {nb.train.median():+.2f}/day')
print('configurations simulated in this script (incl. 20 random seeds per variant):', len(V) * 21 + 20)
