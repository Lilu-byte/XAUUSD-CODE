"""Does changing engine END to 22:45 move the M15/H1 rows of REPORT.md? (engine.py untouched; patched in memory)"""
import sys, os, types; sys.dont_write_bytecode = True
os.environ['NUMBA_DISABLE_CACHING'] = '1'
sys.path.insert(0, '/mnt/project-files/xauusd-intraday/code')
src = open('/mnt/project-files/xauusd-5-a-day/code/engine.py').read().replace('@njit(cache=True)', '@njit')
def mod(s, n):
    m = types.ModuleType(n); exec(compile(s, n, 'exec'), m.__dict__); return m
a = mod(src, 'a'); b = mod(src.replace('END = 23 * 60 + 30', 'END = 22 * 60 + 45'), 'b')
for tf, lo, hi in (('H1', '2016-08-01', '2022-07-01'), ('M15', '2022-07-08', '2026-10-10')):
    P = a.prep(tf)
    for M, name in ((a, '23:30'), (b, '22:45')):
        r = M.sim(P, 'asia_break', 'any', 540, 5, 50); r = r[(r.index >= lo) & (r.index < hi)]
        s = M.summ(r); print(tf, name, round(s['per_day'], 2), 'worst month', round(s['worst_month'], 0), 'dd', round(s['max_dd'], 0))
