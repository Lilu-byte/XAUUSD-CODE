"""ONE-TIME TEST evaluation of the 3 picks chosen on TRAIN, plus the pre-registered train-vs-test sign check of the
family's fill-free effects (diagnostic only, nothing is re-selected from it)."""
import sys, json; sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/momentum-reversion')
from library import *
H = Harness(); m = H.m1; f = build(m); L = library(m, f); ok = valid_mask(m, f)
b = sg(f.body.values)
PICKS = {
    # name: (signal, tp, sl, timeout, max_open)
    'spike_fade_vwap': (-L['r1>3a|vw'], 0.5, 5, 5, 1),
    'pullback_vwap': (pullback(f, 3, 3) * ok, 0.7, 8, 3, 1),
    'range_exp_fade': (np.where(ok & (f.rexp.values > 2.5) & (f.atrq.values > .5), -b, 0).astype(float), 0.5, 8, 10, 3),
}
out = {}
pd.set_option('display.width', 250)
for name, (sig, tp, sl, to, mo) in PICKS.items():
    r = {}
    d, t = H.run(sig, tp, sl, to, mo); r['train'] = summarize(d, t, 'train'); r['test'] = summarize(d, t, 'test')
    d, t = H.run(sig, tp, sl, to, mo, fill='OHLC'); r['test_ohlc'] = summarize(d, t, 'test')
    d, t = H.run(sig, tp, sl, to, mo, spread='bar'); r['test_bar'] = summarize(d, t, 'test')
    d, t = H.run(sig, tp, sl, to, mo, spread='wide'); r['test_wide'] = summarize(d, t, 'test')
    rnd = [summarize(*H.run(random_like(sig, s), tp, sl, to, mo), 'test')['per_day'] for s in range(20)]
    r['test_random_per_day'] = float(np.mean(rnd)); r['test_random_sd'] = float(np.std(rnd))
    e = edge(m, sig); r['edge'] = e.round(3).to_dict(orient='index')
    hk = min((1, 2, 3, 5, 10), key=lambda k: abs(k - to))
    r['edge_h'] = hk
    out[name] = r
    print(f'\n=== {name}: TP {tp} SL {sl} timeout {to} max_open {mo}')
    for k in ('train', 'test', 'test_ohlc', 'test_bar', 'test_wide'):
        s = r[k]; print(f'  {k:10s} per_day {s["per_day"]:+6.2f}  trades/day {s["trades_day"]:5.1f}  win {s["win"]:.2f}  per_trade {s["per_trade"]:+.3f}  days>=5 {s["days_ge5"]:.2f}  worst {s["worst_day"]:+6.1f}  maxDD {s["max_dd"]:+6.1f}')
    print(f'  random-direction same bars (TEST, 20 seeds): {r["test_random_per_day"]:+.2f}/day (sd {r["test_random_sd"]:.2f})')
    print(e.round(3).to_string())
json.dump(out, open('final_test.json', 'w'), indent=1, default=float)

# ---- pre-registered diagnostic: does each fill-free effect keep its sign from TRAIN to TEST? ----
F = fwd(m, (1, 3, 5, 10)); spr = spread_series(m, 'base'); tr = m.index < SPLIT; te = ~tr
rows = []
for name, d in L.items():
    s = d != 0
    if (s & tr).sum() < 50 or (s & te).sum() < 50: continue
    r = dict(sig=name, n_tr=(s & tr).sum() / 47, n_te=(s & te).sum() / len(np.unique(m.index[te].date)))
    for k in (1, 3, 5, 10):
        x = F[k] * d
        r[f'tr{k}'] = np.nanmean(x[s & tr]); r[f'te{k}'] = np.nanmean(x[s & te])
    r['spr_te'] = spr[s & te].mean()
    rows.append(r)
g = pd.DataFrame(rows); g.to_csv('sign_check.csv', index=False)
print('\n=== sign check over', len(g), 'library signals (follow direction; fade = negative)')
for k in (1, 3, 5, 10):
    big = g[np.abs(g[f'tr{k}']) > g.spr_te * 0 + 0.1]
    print(f'  h={k:2d}: same sign {(np.sign(g[f"tr{k}"]) == np.sign(g[f"te{k}"])).mean():.2f}; '
          f'among |train move|>$0.10: {(np.sign(big[f"tr{k}"]) == np.sign(big[f"te{k}"])).mean():.2f} (n={len(big)}); '
          f'corr train/test {np.corrcoef(g[f"tr{k}"], g[f"te{k}"])[0, 1]:.2f}; '
          f'TEST |move|>spread: {(np.abs(g[f"te{k}"]) > g.spr_te).sum()} signals')
key = ['r1>3$', 'r3>6$', 'r3>4$', 'rexp>2.5', 'rexp>3', 'z20>2.5', 'z60>2.5', 'rsi3_ext5', 'rsi7_ext10', 'r1>3a|vw', 'r3>3a|avw',
       'r3>2.5a|avw', 'r1>1.5a|avw', 'vspike>4', 'streak>=7', 'streak>=5', 'r1_any', 'body_any', 'ib_break_mother', 'cloc_ext0.2', 'bb20_touch', 'vwap>2a']
pd.set_option('display.max_rows', 100)
print(g.set_index('sig').loc[[k for k in key if k in set(g.sig)], ['n_tr', 'n_te', 'tr1', 'te1', 'tr3', 'te3', 'tr5', 'te5', 'tr10', 'te10', 'spr_te']].round(3).to_string())
