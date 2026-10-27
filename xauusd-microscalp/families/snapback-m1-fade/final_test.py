"""THE ONE TEST RUN (Sep 1 - Oct 9 2026) for the three picks fixed on TRAIN (picks.py). Same battery as on TRAIN.
Writes final_test.json and the TEST trade lists."""
import sys, json
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/snapback-m1-fade')
from evalx import *
from picks import PICKS
m, H = load_all(); f = feats(m)
res = {}
for name, p in PICKS.items():
    out, d, t = battery(H, f, p, 'test')
    tr = summ(d, t, 'train')
    te = t[t.entry >= SPLIT]
    # fill-free view on TEST: average move of the bid close in the trade direction after the next-bar open entry
    s = ea_filter(m, fade_signal(f, *p['sig']))
    sel = (s != 0) & (m.index >= SPLIT)
    mv = {}
    for k in (1, 2, 3, 5, 10, 15):
        x = ((m.close.shift(-k) - m.open.shift(-1)) * s)[sel].dropna(); mv[f'move_{k}m'] = float(x.mean())
    wk = d[d.index >= SPLIT].pnl.groupby(d[d.index >= SPLIT].index.to_period('W')).sum()
    print(f'=== {name}: TRAIN (same full-data run) {tr["per_day"]:+.2f}/day {tr["trades_day"]:.1f} tr/day {tr["per_trade"]:+.3f}/tr')
    print(f'    TEST: exit kinds TP/SL/mixed/time {(te.kind == 0).mean():.2f}/{(te.kind == 1).mean():.2f}/{(te.kind == 2).mean():.2f}/{(te.kind == 3).mean():.2f}; '
          f'avg spread paid (base) n/a; fill-free move from next open (no spread): ' + ', '.join(f'{k} {v:+.2f}' for k, v in mv.items()))
    print('    TEST weekly $: ' + ' '.join(f'{v:+.0f}' for v in wk.values))
    for k, r in out.items(): print(fmt(k, r))
    out['train_same_run'] = tr; out['test_moves'] = mv
    res[name] = out
    te.drop(columns=['ei', 'xi']).to_csv(FAM + f'final_test_trades_{name}.csv', index=False)
json.dump(res, open(FAM + 'final_test.json', 'w'), indent=1, default=float)
