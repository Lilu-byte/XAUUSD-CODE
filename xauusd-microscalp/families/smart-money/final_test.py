"""FINAL: the 3 picks chosen on TRAIN (bracket2.py / robust2.py), evaluated once on TEST.
Run once. Output in final_test.out."""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/smart-money')
from cands import *
from mlib import Harness, summarize, edge, random_like

H = Harness(); m1 = H.m1
C = build2(m1)
PICKS = {'P1_lon_fade_brk30': dict(tp=1.0, sl=10.0, timeout=30, max_open=1),
         'P2_late_sweep30_disp': dict(tp=1.0, sl=5.0, timeout=20, max_open=3),
         'P3_union': dict(tp=1.0, sl=10.0, timeout=30, max_open=1)}
R = lambda d: {k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for k, v in d.items()}
pd.set_option('display.width', 250)
out = {}
for name, p in PICKS.items():
    s = C[name]
    print(f'\n######## {name} {p}')
    days, tr = H.run(s, **p)
    a = summarize(days, tr, 'train'); b = summarize(days, tr, 'test')
    print('TRAIN FAIR/base', R(a)); print('TEST  FAIR/base', R(b))
    tt = tr[tr.entry >= SPLIT]
    print('  test avg bars held %.2f, share exited at timeout-or-later %.3f, test avg win %.3f avg loss %.3f'
          % (tt.bars.mean(), (tt.bars >= p['timeout']).mean(), tt.pnl[tt.pnl > 0].mean(), tt.pnl[tt.pnl <= 0].mean()))
    res = {'train': a, 'test': b}
    for fill, spread in (('OHLC', 'base'), ('FAIR', 'bar'), ('FAIR', 'wide')):
        d2, t2 = H.run(s, fill=fill, spread=spread, **p)
        res[f'{fill}/{spread}'] = summarize(d2, t2, 'test')
        print(f'TEST  {fill}/{spread}', R(res[f'{fill}/{spread}']))
    rp = []
    for seed in range(20):
        d3, t3 = H.run(random_like(s, seed), **p)
        rp.append(summarize(d3, t3, 'test')['per_day'])
    res['rand'] = (np.mean(rp), np.std(rp))
    print('TEST random-direction same bars per_day mean %.3f sd %.3f (20 seeds)' % res['rand'])
    e = edge(m1, s, horizons=(1, 2, 3, 5, 10, 20, 30))
    print(e.round(3).to_string())
    res['edge'] = e
    w = days[days.index >= SPLIT].pnl
    print('  TEST weekly pnl:', w.groupby(w.index.to_period('W')).sum().round(1).tolist())
    print('  TEST daily pnl:', w.round(1).tolist())
    out[name] = res
pd.to_pickle(out, '/mnt/project-files/xauusd-microscalp/families/smart-money/final_test.pkl')
