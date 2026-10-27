"""Compare the C++ translation's stretches (incremental path, nc=2) and its higher-timeframe stretches with the Python prototype."""
import sys; sys.path.insert(0, '/mnt/project-files/xauusd-channels/code')
import numpy as np, pandas as pd, seg
out = open(sys.argv[1]).read().splitlines()
def run(path, first, last, L):
    d = pd.read_csv(path, header=None, skiprows=1)
    o, h, l, c = [d.iloc[first:last + 1, i].values for i in (1, 2, 3, 4)]
    segs, ev = seg.segment(o, h, l, c, L, 0.2, 0.6, k=2.0, nc=2)
    return [(s + first, e + first, lab) for s, e, lab in segs[:-1]], [(t + first, dd) for t, dd in ev], segs[-1][0] + first
py, pyb, live = run('/tmp/claude-0/h1_6000.csv', 3500 - 1 - 3000, 6000 - 2, 20)
cpp = [tuple(map(int, x.split()[1:])) for x in out if x.startswith('S ')]
br = [tuple(map(int, x.split()[1:])) for x in out if x.startswith('B ')]
print('chart: stretches python', len(py), 'c++', len(cpp), 'identical:', py == cpp, '| breaks identical:', pyb == br)
hpy, _, _ = run('/tmp/claude-0/d1_3001.csv', 1, 3001 - 2, 20)
hc = [tuple(map(int, x.split()[1:])) for x in out if x.startswith('HS ')]
print('higher timeframe: python', len(hpy), 'c++', len(hc), 'identical:', hpy == hc)
