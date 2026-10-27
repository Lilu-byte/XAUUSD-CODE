"""FINAL scoring, run once. Rules frozen from grid.py / grid2.py / grid3.py (train 2016-07..2021-12 only):
  H1, long only. Entry: H1 close > highest high of the prior 120 H1 bars, while the last CLOSED D1 close > D1 SMA(200);
  buy 0.01 at the next H1 open. Initial stop entry - 2*ATR(14) (signal bar). After every closed H1 bar:
  stop = max(stop, highest high since entry - 4*ATR(14) of that bar). No target.
  Pyramid: first H1 close >= entry1 + 2*ATR(14 at signal) -> buy a 2nd 0.01 at the next open and raise the
  shared stop to at least entry1 (breakeven). One add per trade; both units close on the shared stop.
"""
from common import *
import json
OUT = '/mnt/project-files/xauusd-github-bots/capitalize/trend-exits/'
d = load('H1'); a = atr(d, 14); reg = d1_regime(d, 200)
sig = np.where(reg, dc_sig(d, 120), 0.0)
CFG = {'pick: pyramid +2ATR': dict(sl=2 * a, trail_m=4.0, add_trig=2.0, max_units=2),
       'same, no pyramid': dict(sl=2 * a, trail_m=4.0)}
res = {}
for name, kw in CFG.items():
    t = tx.tsim(d, sig, a, **kw)
    out = {}
    for w, (s0, s1) in {'train': TRAIN, 'test': TEST, 'common': COMMON, 'all': ('2016-07-29', '2026-10-10')}.items():
        r = tx.summary(t, d, s0, s1)
        eq = tx.mtm_daily(t[(t.entry_time >= pd.Timestamp(s0)) & (t.entry_time < pd.Timestamp(s1))], d)
        eq = eq[(eq.index >= pd.Timestamp(s0)) & (eq.index < pd.Timestamp(s1))]
        r['mtm_dd'] = round((eq - eq.cummax()).min(), 0); out[w] = r
    out['by_year'] = tx.by_year(t, d).to_dict()
    res[name] = (t, out)
    print(f'== {name}')
    for w in ('train', 'test', 'common', 'all'):
        print(f'  {w:6s}', json.dumps({k: v for k, v in out[w].items() if k != "label"}, default=str))
    print('  by year', out['by_year'])
print('hold gold: train', hold_gold(d, *TRAIN), '\n  test', hold_gold(d, *TEST), '\n  common', hold_gold(d, *COMMON))
print('  hold by year', hold_by_year(d))
t, out = res['pick: pyramid +2ATR']
t.drop(columns=['ei', 'xi']).to_csv(OUT + 'trades_pick.csv', index=False)
pd.DataFrame({k: v[1]['by_year'] for k, v in res.items()} | {'hold 0.01 lot': hold_by_year(d)}).to_csv(OUT + 'by_year.csv')
t0, out0 = res['same, no pyramid']
t0.drop(columns=['ei', 'xi']).to_csv(OUT + 'trades_final_nopyramid.csv', index=False)
rows = []
for name, (_, o) in res.items():
    for w in ('train', 'test', 'common', 'all'):
        rows.append(dict(version=name, window=w, **{k: v for k, v in o[w].items() if k != 'label'}))
pd.DataFrame(rows).to_csv(OUT + 'summary_final.csv', index=False)
