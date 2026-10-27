"""Circular time-shift test with the gbt-based runner: share of shifted copies of each position series that the real
timing beats on $/day in the test window (diagnostics.py reports beats_shifted_test). Usage: python3 -I shift_check.py"""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest')
import numpy as np, pandas as pd
import gbt, mm
from verify import rule_positions, run, daily, W

OUT = '/mnt/project-files/xauusd-github-bots/market-matrix/verify-backtest/'
res = {}
for tf, names in (('H4', ['a_MA_stack']), ('D1', ['c_MACD_line']), ('H1', ['d_RangeOsc_break', 'e_all_5of7'])):
    d = gbt.load(tf); p, _ = mm.all_panels(d); P = rule_positions(tf, p)
    for nm in names:
        pos = P[nm]; n = len(pos); rng = np.random.default_rng(11)
        def pdm(x, w):
            t, bf, bs, dx = run(d, x); return daily(bf, dx).loc[w[0]:w[1]].mean()
        real = {wn: pdm(pos, W[tf][wn]) for wn in ('train', 'test')}
        sh = {'train': [], 'test': []}
        for _ in range(100):
            k = int(rng.integers(n // 10, n - n // 10)); x = np.roll(pos, k)
            t, bf, bs, dx = run(d, x); dd = daily(bf, dx)
            for wn in sh: sh[wn].append(dd.loc[W[tf][wn][0]:W[tf][wn][1]].mean())
        res[f'{tf} {nm}'] = {wn: dict(real=round(real[wn], 3), shifted_median=round(float(np.median(sh[wn])), 3),
                                      beats_pct=float(100 * (np.array(sh[wn]) < real[wn]).mean())) for wn in sh}
        print(tf, nm, res[f'{tf} {nm}'], flush=True)
json.dump(res, open(OUT + 'shift_results.json', 'w'), indent=1)
