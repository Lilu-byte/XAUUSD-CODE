"""FINAL: the 3 picks fixed on TRAIN, evaluated once on TEST (2026-09-01 onward)."""
from sigs import *
H = Harness(); m = H.m1
f = forming(m, 5); c5 = resample(m, 5)
avg5 = htf_on_m1(m, c5, 'M5', (c5.close - c5.open).abs().rolling(20).mean().values).values
body = np.abs(f.f_close - f.f_open).values; rng = (f.f_high - f.f_low).values; col = np.sign(f.f_close - f.f_open).values
t15 = trend(m, 'M15')
s_form = np.where((f.f_minute.values == 3) & (body >= avg5) & (body >= 0.9 * rng) & (col == -t15), -col, 0)
s1 = pullback(m, 2, False, 1.0, 0.9, 'H1'); s2 = pullback(m, 3, False, 2.0, 0.9, 'H1'); s2b = pullback(m, 3, False, 2.0, 0.9, 'M15')
U = np.sign(s1 + s2b + s_form)
PICKS = [('PB_M2_H1', s1, dict(tp=1.0, sl=5, timeout=20, max_open=3)),
         ('PB_M3_H1', s2, dict(tp=0.75, sl=8, timeout=20, max_open=1)),
         ('PB_union', U, dict(tp=1.0, sl=8, timeout=10, max_open=3))]
pd.set_option('display.width', 250)
r3 = lambda d: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
for name, sig, p in PICKS:
    print(f'\n######## {name} {p}')
    d, t = H.run(sig, **p)
    print('TRAIN FAIR/base', r3(summarize(d, t, 'train')))
    st = summarize(d, t, 'test'); print('TEST  FAIR/base', r3(st))
    tt = t[t.entry >= SPLIT]; print('  test avg bars held', round(tt.bars.mean(), 2), 'exit by timeout share', round((tt.bars >= p['timeout']).mean(), 3))
    for fill, spr in (('OHLC', 'base'), ('FAIR', 'bar'), ('FAIR', 'wide')):
        d2, t2 = H.run(sig, fill=fill, spread=spr, **p); print(f'TEST  {fill}/{spr}', r3(summarize(d2, t2, 'test')))
    rr = [summarize(*H.run(random_like(sig, s), **p), 'test')['per_day'] for s in range(20)]
    print('TEST random-direction same bars per_day mean %.3f sd %.3f' % (np.mean(rr), np.std(rr)))
    e = edge(m, sig, horizons=(1, 2, 3, 5, 10, 20))
    print(e.round(3).to_string())
    td = d[d.index >= SPLIT]; print('  TEST weekly pnl:', td.pnl.resample('W').sum().round(1).tolist())
