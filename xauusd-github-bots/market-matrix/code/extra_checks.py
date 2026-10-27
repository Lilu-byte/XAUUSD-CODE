"""Timing test (200 time-shifted copies) for the three long-only readings in REPORT.md's second table; saves extra_checks.json.
Usage: python3 -I extra_checks.py"""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, gbt, mm
from test_rules import rules, shift_test, WIN, OUT
out = {}
for tf, name in [('H4', 'MA stack 20/50/200'), ('H4', 'MACD line sign'), ('H1', 'Range Osc +/-100 breakout, exit at 0')]:
    d = gbt.load(tf); p, _ = mm.all_panels(d); R, _ = rules(p); pos = np.clip(np.asarray(R[name], int), 0, 1)
    out[f'{tf} {name} long only'] = {'beats_shifted_train_pct': shift_test(d, pos, WIN[tf]['train'], runs=200),
                                     'beats_shifted_test_pct': shift_test(d, pos, WIN[tf]['test'], runs=200)}
    print(tf, name, out[f'{tf} {name} long only'], flush=True)
json.dump(out, open(OUT + 'extra_checks.json', 'w'), indent=1)
