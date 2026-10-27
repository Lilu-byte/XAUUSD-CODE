import gridsim as g, itertools, pandas as pd
from multiprocessing import Pool
d = g.load('m1.csv')
parts = {'tune Jun26-Aug31': d[d.t < '2026-09-01'].reset_index(drop=True),
         'test Sep1-Oct9': d[d.t >= '2026-09-01'].reset_index(drop=True)}
jobs = list(itertools.product(parts, [0.2, 0.5, 1, 2, 5], [0.1, 0.2],
                              [None, 0.3, 0.5, 1, 2, 5, 20], ['candle', 'random', 'against']))
def f(j):
    p, G, TP, SL, dm = j
    r = g.run(parts[p], G, TP, SL, dirmode=dm); r['period'] = p; return r
if __name__ == '__main__':
    with Pool(8) as pool: rs = pool.map(f, jobs, chunksize=4)
    pd.DataFrame(rs).to_csv('grid_m1.csv', index=False)
