"""TRAIN-only: spike-bar fades (strong 1-2 bar mean reversion) + reference brackets via the harness.
Direction = trade direction (fade)."""
import sys, itertools; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from sigs import *
from scan_lib import Scanner
H = Harness(); m = H.m1; f = build(m); S = Scanner(m, f); ok = valid_mask(m, f)
b = sg(f.body.values); rng = f.rng.values; a240 = f.atr240.values; ap20 = f.atr_prev20.values
body_frac = np.abs(f.body.values) / np.where(rng > 0, rng, np.nan)
cl = f.cloc.values; vs = sg(f.vw_d.values)
REF = [(1.0, 5, 3), (0.5, 3, 3), (0.3, 2, 2)]   # tp, sl, timeout reference brackets (max_open 1)
ref_rows = []
filters = {
    'all': np.ones(len(m), bool),
    'vwapside': None, 'antivwap': None,
    'body>.6': body_frac > .6,
    'closeext': (cl > .8) | (cl < .2),
    'wick': None,   # close retraced from the extreme: bull bar with cloc<.7 / bear bar with cloc>.3
    'vrel>2': f.vrel.values > 2,
    'vreg>1.2': f.vreg.values > 1.2,
}
cnt = 0
for base, thr_list, ref in (('rng/ap20', (2, 2.5, 3, 4), ap20), ('rng/a240', (2, 2.5, 3, 4), a240), ('body/a240', (1.5, 2, 2.5, 3), a240)):
    x = (rng if base.startswith('rng') else np.abs(f.body.values)) / ref
    for th in thr_list:
        fade = np.where(x > th, -b, 0).astype(float)
        for fn, flt in filters.items():
            if fn == 'vwapside': flt = vs == fade
            elif fn == 'antivwap': flt = vs == -fade
            elif fn == 'wick': flt = ((b > 0) & (cl < .7)) | ((b < 0) & (cl > .3))
            d = np.where(flt & ok, fade, 0)
            name = f'{base}>{th}|{fn}'
            r = S.add(name, d)
            for tp, sl, to in REF:
                days, trades = H.run(d, tp, sl, to, 1)
                s = summarize(days, trades, 'train')
                r[f'pt_{tp}'] = s['per_trade']; r[f'pd_{tp}'] = s['per_day']
            cnt += 1
t = S.table()
for k in (1, 2, 3, 5):
    t[f'n{k}'] = t[f'm{k}T'] - t.sprT; t[f'n{k}A'] = t[f'm{k}A'] - t.sprA; t[f'n{k}B'] = t[f'm{k}B'] - t.sprB
t.to_csv('scan4_train.csv')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
cols = ['nT', 'sprT', 'n1', 'n2', 'n3', 'n5', 'n1A', 'n1B', 'n2A', 'n2B', 'pt_1.0', 'pd_1.0', 'pt_0.5', 'pd_0.5', 'pt_0.3', 'pd_0.3']
print(t[cols].sort_values('pd_1.0', ascending=False).head(30).round(3).to_string())
print('signals', cnt, ' x3 ref brackets')
