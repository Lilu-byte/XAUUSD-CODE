"""Stage B (TRAIN only, mlib v2): management layer on top of Stage A brackets.
signal x bracket (top-3 per signal from Stage A by per_trade + 6 'user-style' brackets)
x spread gate (none, recorded spread of bar i <= 0.10/0.15/0.20, of bar i-1 <= 0.10)
x max_open (1,3,5,10,50) x cooldown (0,1,3,5,10).  Writes stageB2_train.csv.
Plus a break-even-stop sub-grid (stop moved to entry+lock once a bar closes >= trig in profit)."""
from sigs2 import *
from multiprocessing import Pool
import itertools, time

USER = [(0.10, 5.0, 30), (0.20, 20.0, 30), (0.30, 0.30, 3), (0.50, 2.0, 10), (1.00, 0.50, 10), (0.75, 50.0, 3)]
GATES = [(None, 0), (0.10, 0), (0.15, 0), (0.20, 0), (0.10, 1)]
MO = [1, 3, 5, 10, 50]
CD = [0, 1, 3, 5, 10]
BE = [(0.2, 0.0), (0.3, 0.05), (0.5, 0.0), (0.5, 0.2)]
SIGS = ['AB', 'CF', 'COL', 'HTF', 'PB', 'MR', 'MR6']
G = {}


def init():
    m1, H = train_harness(); S = build(m1); tr = m1.index < SPLIT
    G['H'] = H; G['S'] = {}
    for k in SIGS:
        for g, lag in GATES:
            G['S'][(k, g, lag)] = (S[k] if g is None else gate(S[k], m1, g, lag))[tr]


def job(a):
    sname, (tp, sl, to), (g, lag), mo, cd, (bt, bl) = a
    d, t = run_pw(G['H'], G['S'][(sname, g, lag)], tp, sl, timeout=to, max_open=mo, cooldown=cd, be_trig=bt, be_lock=bl)
    r = summ(d, t, 'train')
    r.update(sig=sname, tp=tp, sl=sl, timeout=to, gate=g if g else 0, lag=lag, max_open=mo, cooldown=cd, be_trig=bt,
             be_lock=bl, avg_spr=t.spr.mean() if len(t) else np.nan, avg_bars=t.bars.mean() if len(t) else np.nan)
    r['resid'] = r['per_trade'] + r['avg_spr']
    return r


if __name__ == '__main__':
    t0 = time.time()
    A = pd.read_csv(OUT + 'stageA2_train.csv')
    jobs = []
    for s in SIGS:
        gA = A[A.sig == s]
        top = gA.sort_values('per_trade', ascending=False).head(3)
        bases = list(dict.fromkeys([(r.tp, r.sl, int(r.timeout)) for r in top.itertuples()] + USER))
        jobs += list(itertools.product([s], bases, GATES, MO, CD, [(0.0, 0.0)]))
        wide = [b for b in bases if b[1] >= 2.0]
        jobs += list(itertools.product([s], wide, GATES[:2], [1, 5], [0], BE))
    with Pool(4, initializer=init) as p:
        rows = p.map(job, jobs, chunksize=25)
    R = pd.DataFrame(rows)
    R.to_csv(OUT + 'stageB2_train.csv', index=False)
    print('configs', len(R), 'secs %.0f' % (time.time() - t0))
    pd.set_option('display.width', 250)
    c = ['sig', 'tp', 'sl', 'timeout', 'gate', 'lag', 'max_open', 'cooldown', 'be_trig', 'per_day', 'trades_day', 'pwin',
         'per_trade', 'avg_spr', 'resid', 'worst_day', 'max_dd', 'pd_jul', 'pd_aug']
    print('positive TRAIN per_day:', (R.per_day > 0).sum(), ' both halves > 0:', ((R.pd_jul > 0) & (R.pd_aug > 0)).sum(),
          ' per_day >= 5:', (R.per_day >= 5).sum())
    q = R[(R.pd_jul > 0) & (R.pd_aug > 0)]
    print('\ntop 25 by per_day with both inner halves > 0:')
    print(q.sort_values('per_day', ascending=False)[c].head(25).round(3).to_string(index=False))
    b = R[R.be_trig == 0]
    print('\nmedian per_trade / resid by max_open (no BE):'); print(b.groupby('max_open')[['per_trade', 'resid', 'per_day', 'trades_day']].median().round(3))
    print('\nmedian per_trade / resid by cooldown:'); print(b.groupby('cooldown')[['per_trade', 'resid', 'per_day', 'trades_day']].median().round(3))
    print('\nmedian per_trade / avg_spr / resid by gate:'); print(b.groupby(['gate', 'lag'])[['per_trade', 'avg_spr', 'resid', 'trades_day']].median().round(3))
    print('\nper signal: median resid / best per_day:')
    print(b.groupby('sig').agg(resid_med=('resid', 'median'), pt_best=('per_trade', 'max'), pd_best=('per_day', 'max')).round(3))
    be = R[(R.max_open.isin([1, 5])) & (R.cooldown == 0) & (R.gate.isin([0, 0.10])) & (R.lag == 0) & (R.sl >= 2.0)]
    key = ['sig', 'tp', 'sl', 'timeout', 'gate', 'max_open']
    base = be[be.be_trig == 0].set_index(key)[['per_trade', 'pwin']]
    for (bt, bl), gB in be[be.be_trig > 0].groupby(['be_trig', 'be_lock']):
        x = gB.set_index(key)[['per_trade', 'pwin']].join(base, rsuffix='_noBE', how='inner')
        print(f'BE trig {bt} lock {bl}: n {len(x)}  median per_trade change {(x.per_trade - x.per_trade_noBE).median():+.4f} '
              f' (range {(x.per_trade - x.per_trade_noBE).min():+.3f}..{(x.per_trade - x.per_trade_noBE).max():+.3f}),'
              f' median pwin change {(x.pwin - x.pwin_noBE).median():+.3f}')
