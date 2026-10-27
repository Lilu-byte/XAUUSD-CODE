"""Scratch checks for REPORT 'Test results' section. Writes only to verify-final/."""
import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code')
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/market-matrix/code')
import numpy as np, pandas as pd
import gbt, mm
from test_rules import sim, per_day, rules, shift_test, WIN, RECENT, COMMON

out = {}
store = pd.read_pickle('/mnt/project-files/xauusd-github-bots/market-matrix/code/_bar_pnl.pkl')


def sharpe_raw(pb, d, w):
    p = per_day(pb.loc[w[0]:w[1]])
    px = d.close.groupby(d.index.normalize()).last().shift().reindex(p.index)
    r = p / px
    return float(r.mean() / r.std() * np.sqrt(252)), float(p.mean()), float((p.cumsum() - p.cumsum().cummax()).min())


raw = {}
for tf in ('D1', 'H4', 'H1'):
    d = gbt.load(tf)
    for (t, name, mode), pb in store.items():
        if t != tf:
            continue
        for wn, w in (('train', WIN[tf]['train']), ('test', WIN[tf]['test'])):
            raw[f'{tf}|{name}|{mode}|{wn}'] = sharpe_raw(pb, d, w)
    if tf == 'H4':
        p, _ = mm.all_panels(d)
        R, _ = rules(p)
        pos = np.clip(np.asarray(R['MACD line sign'], int), 0, 1)
        out['H4_MACD_line_lo_shift'] = dict(train=shift_test(d, pos, WIN['H4']['train'], runs=100),
                                            test=shift_test(d, pos, WIN['H4']['test'], runs=100),
                                            train200=shift_test(d, pos, WIN['H4']['train'], runs=200),
                                            test200=shift_test(d, pos, WIN['H4']['test'], runs=200))
        pos2 = np.clip(np.asarray(R['MA stack 20/50/200'], int), 0, 1)
        out['H4_MA_stack_lo_shift'] = dict(train=shift_test(d, pos2, WIN['H4']['train'], runs=100),
                                           test=shift_test(d, pos2, WIN['H4']['test'], runs=100))
    print(tf, 'done', flush=True)

keys = ['H4|MA stack 20/50/200|long only', 'H4|MACD line sign|long only', 'H4|Hold 0.01 lot long|long only',
        'H1|Range Osc +/-100 breakout, exit at 0|long only', 'H1|Hold 0.01 lot long|long only',
        'D1|ASI vs its signal|long only', 'D1|Hold 0.01 lot long|long only']
out['raw'] = {k + '|' + wn: raw[k + '|' + wn] for k in keys for wn in ('train', 'test')}
# unrounded medians
med = {}
for tf in ('D1', 'H4', 'H1'):
    for mode in ('long+short', 'long only'):
        v = [raw[k][0] for k in raw if k.startswith(tf + '|') and f'|{mode}|test' in k and 'Hold' not in k]
        med[f'{tf}|{mode}'] = (len(v), float(np.median(v)))
out['median_test_sharpe_unrounded'] = med
json.dump(out, open('/mnt/project-files/xauusd-github-bots/market-matrix/verify-final/check_tr.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
