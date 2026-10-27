import pandas as pd, numpy as np, sim2, itertools, sys
from multiprocessing import Pool
tf = sys.argv[1]
x = pd.read_pickle(f'live_{tf}.pkl'); x.attrs['mins'] = 1 if tf == 'M1' else 5
parts = {'M1': {'tune': x['2026-06-26':'2026-08-31'], 'test': x['2026-09-01':]},
         'M5': {'all': x}}[tf]
for v in parts.values(): v.attrs['mins'] = x.attrs['mins']
cfgs = []
for dd, mode, maxpos, W, lab in itertools.product(
        [('d', 0.5), ('d', 1), ('d', 2), ('d', 3), ('d', 5), ('f', 0.25), ('f', 0.5)],
        [('none', 0), ('close', 0), ('x', 1), ('x', 2), ('x', 4), ('edge', 0), ('brk', 0)],
        [1, 5, 50], [0, 5, 10], ['any', 'range']):
    cfgs.append(dict(d=dd[1] if dd[0] == 'd' else 0, dfrac=dd[1] if dd[0] == 'f' else None, mode=mode[0], k=mode[1],
                     maxpos=maxpos, W=W, lab=None if lab == 'any' else (0,), label=lab))
def one(cf):
    out = []
    for name, part in parts.items():
        a = {k: v for k, v in cf.items() if k != 'label'}
        r = sim2.run(part, **a)[0]
        out.append(dict(part=name, d=cf['d'], dfrac=cf['dfrac'], mode=cf['mode'], k=cf['k'], maxpos=cf['maxpos'],
                        W=cf['W'], lab=cf['label'], **r))
    return out
if __name__ == '__main__':
    with Pool(4) as pool: res = pool.map(one, cfgs, chunksize=4)
    df = pd.DataFrame([r for rr in res for r in rr]); df.to_csv(f'grid_{tf}.csv', index=False); print(len(df))
